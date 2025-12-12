from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.runnables import RunnableConfig
from agent.infra.redis_checkpointer import RedisCheckpointer
from agent.tools.project_tools import (
    search_project_by_name,
    get_all_projects,
    search_task_in_project,
    get_all_tasks_in_project,
    create_timesheet_entry,
    create_multiple_timesheet_entries,
    get_timesheet_entries_by_date_range,
    Context,
)
from agent.core.prompts import TIMESHEET_AGENT_SYSTEM_PROMPT
from app.shared.security.dependencies import get_current_user
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from datetime import date, datetime
import locale


load_dotenv()

# Configurar locale para fechas en español (una sola vez al cargar el módulo)
try:
    locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
except:
    try:
        locale.setlocale(locale.LC_TIME, "es_ES")
    except:
        pass  # Si no se puede configurar, continuar con el locale por defecto


def get_current_date_formatted() -> str:
    """Obtiene la fecha actual formateada en español."""
    return datetime.now().strftime("%d/%m/%Y, %A")


def create_timesheet_agent():
    """
    Crea y configura el agente de timesheets.

    Returns:
        tuple: (agent, checkpointer) - El agente configurado y el checkpointer para mantener estado
    """
    # Configurar el modelo
    model = init_chat_model(
        model="openai:gpt-5-mini",
    )

    # Formatear el prompt del sistema con un placeholder para la fecha
    # La fecha real se inyectará en cada invocación
    prompt = PromptTemplate.from_template(TIMESHEET_AGENT_SYSTEM_PROMPT).format(
        today_date="{dynamic_date}"
    )

    # Crear checkpointer Redis para mantener el estado de las conversaciones
    # Las conversaciones expiran automáticamente después del TTL configurado
    checkpointer = RedisCheckpointer()

    # Crear el agente con todas las herramientas
    agent = create_agent(
        model=model,
        system_prompt=prompt,
        tools=[
            search_project_by_name,
            get_all_projects,
            search_task_in_project,
            get_all_tasks_in_project,
            create_timesheet_entry,
            create_multiple_timesheet_entries,
            get_timesheet_entries_by_date_range,
        ],
        context_schema=Context,
        checkpointer=checkpointer,
    )

    return agent, checkpointer


def run_agent(agent, message: str, conversation_id: str, employee_id: int) -> str:
    """
    Ejecuta el agente de forma síncrona (sin streaming) y retorna la respuesta completa.

    Args:
        agent: El agente configurado a ejecutar
        message: Mensaje del usuario
        conversation_id: ID único de la conversación para mantener contexto
        employee_id: ID del empleado que hace la consulta

    Returns:
        str: Respuesta completa del agente
    """
    # Configurar el contexto de la conversación
    config: RunnableConfig = {"configurable": {"thread_id": conversation_id}}

    # Inyectar la fecha actual en cada invocación para evitar fechas stale
    current_date = get_current_date_formatted()
    date_context = f"[Fecha actual del sistema: {current_date}]"

    # Ejecutar el agente con la fecha actual inyectada
    response = agent.invoke(
        {
            "messages": [
                {"role": "system", "content": date_context},
                {"role": "user", "content": message},
            ]
        },
        config=config,
        context=Context(employee_id=employee_id),
    )

    # Extraer solo el contenido del texto del último mensaje
    last_message = response["messages"][-1]

    if hasattr(last_message, "content"):
        content = last_message.content

        # Si content es una lista, extraer solo los campos 'text'
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    text_parts.append(item["text"])
                elif isinstance(item, str):
                    text_parts.append(item)
            return "\n".join(text_parts)

        # Si content es un string, retornarlo directamente
        return content
    else:
        return str(last_message)


def run_agent_stream(agent, message: str, conversation_id: str, employee_id: int):
    """
    Ejecuta el agente con streaming y genera chunks de la respuesta en tiempo real.

    Args:
        agent: El agente configurado a ejecutar
        message: Mensaje del usuario
        conversation_id: ID único de la conversación para mantener contexto
        employee_id: ID del empleado que hace la consulta

    Yields:
        dict: Diccionario con 'type' ('text' o 'event') y 'content'
    """
    import json

    # Configurar el contexto de la conversación
    config: RunnableConfig = {"configurable": {"thread_id": conversation_id}}

    # Inyectar la fecha actual en cada invocación para evitar fechas stale
    current_date = get_current_date_formatted()
    date_context = f"[Fecha actual del sistema: {current_date}]"

    try:
        # Ejecutar el agente en modo streaming con la fecha actual inyectada
        for token, metadata in agent.stream(
            {
                "messages": [
                    {"role": "system", "content": date_context},
                    {"role": "user", "content": message},
                ]
            },
            config=config,
            context=Context(employee_id=employee_id),
            stream_mode="messages",
        ):
            # Obtener el nombre del nodo actual
            node = (
                metadata.get("langgraph_node") if isinstance(metadata, dict) else None
            )

            # Procesar respuestas del modelo (texto)
            if node == "model":
                # Procesar los content_blocks (basado en el ejemplo del usuario)
                content_blocks = getattr(token, "content_blocks", [])

                for block in content_blocks:
                    # Solo emitir chunks de texto (ignorar tool_calls)
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_chunk = block.get("text", "")
                        if text_chunk:
                            yield {"type": "text", "content": text_chunk}

            # Detectar cuando se ejecutan herramientas y verificar si se creó un timesheet
            elif node == "tools":
                # El token contiene el resultado de la herramienta
                content = getattr(token, "content", None)

                if content:
                    try:
                        # Intentar parsear el contenido como JSON
                        result = (
                            json.loads(content) if isinstance(content, str) else content
                        )

                        # Verificar si es una respuesta exitosa de creación de timesheet
                        if isinstance(result, dict) and result.get("success") is True:
                            # Enviar evento especial al frontend
                            yield {
                                "type": "event",
                                "event": "timesheet_created",
                                "content": {"success": True},
                            }
                    except (json.JSONDecodeError, AttributeError):
                        # Si no se puede parsear, ignorar
                        pass

    except Exception as e:
        # Log error but don't print stack trace in production
        print(f"Error in agent stream: {e}")
        raise
