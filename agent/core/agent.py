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
from typing import Any, cast
from langchain.agents.middleware import AgentMiddleware, HumanInTheLoopMiddleware

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
        middleware=cast(
            "list[AgentMiddleware[Any, Context]]",
            [
                HumanInTheLoopMiddleware(
                    interrupt_on={
                        "create_timesheet_entry": True,  # Interrumpir y permitir approve/reject
                    },
                ),
            ],
        ),
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
        dict: Diccionario con 'type' ('text', 'event', 'interrupt') y 'content'
    """
    import json

    # Configurar el contexto de la conversación
    config: RunnableConfig = {"configurable": {"thread_id": conversation_id}}

    # Inyectar la fecha actual en cada invocación para evitar fechas stale
    current_date = get_current_date_formatted()
    date_context = f"[Fecha actual del sistema: {current_date}]"

    try:
        # Ejecutar el agente en modo streaming con la fecha actual inyectada
        for mode, chunk in agent.stream(
            {
                "messages": [
                    {"role": "system", "content": date_context},
                    {"role": "user", "content": message},
                ]
            },
            config=config,
            context=Context(employee_id=employee_id),
            stream_mode=["updates", "messages"],
        ):
            # Modo "messages": tokens del LLM
            if mode == "messages":
                token, metadata = chunk
                
                # Filtrar mensajes de herramientas (ToolMessage)
                # Solo queremos enviar el texto que el modelo escribe al usuario
                message_type = type(token).__name__
                if message_type == "ToolMessage":
                    # No enviar respuestas de herramientas al frontend
                    continue
                
                content_blocks = getattr(token, "content_blocks", [])

                for block in content_blocks:
                    # Solo emitir chunks de texto (ignorar tool_calls)
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_chunk = block.get("text", "")
                        if text_chunk:
                            # Filtro adicional: no enviar si parece ser JSON de herramienta
                            if text_chunk.strip().startswith("{") and (
                                "search_term" in text_chunk or 
                                "project_id" in text_chunk or
                                "found" in text_chunk or
                                "tasks" in text_chunk
                            ):
                                continue
                            
                            yield {"type": "text", "content": text_chunk}

            # Modo "updates": actualizaciones del grafo (incluye interrupciones)
            elif mode == "updates":
                # Detectar interrupciones de Human-in-the-Loop
                if isinstance(chunk, dict) and "__interrupt__" in chunk:
                    # Extraer información de la interrupción
                    interrupts = chunk["__interrupt__"]
                    
                    if interrupts:
                        # Convertir el objeto Interrupt a dict serializable
                        interrupt_data = []
                        for interrupt in interrupts:
                            if hasattr(interrupt, 'value'):
                                interrupt_data.append(interrupt.value)
                            elif isinstance(interrupt, dict):
                                interrupt_data.append(interrupt)
                        
                        # Enviar interrupción al frontend para que el usuario decida
                        yield {
                            "type": "interrupt",
                            "content": interrupt_data
                        }
                        # IMPORTANTE: Detener el streaming aquí porque la ejecución está pausada
                        # El usuario debe responder con approve/reject para reanudar
                        return
                
                # También detectar cuando se ejecutan herramientas exitosamente
                # para enviar notificaciones al frontend
                for node_name, node_update in chunk.items():
                    if node_name == "tools" and isinstance(node_update, dict):
                        # El node_update contiene información sobre la ejecución de herramientas
                        messages = node_update.get("messages", [])
                        for msg in messages:
                            content = getattr(msg, "content", None)
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
        print(f"Error in agent stream: {e}")
        raise


def resume_agent_stream(agent, conversation_id: str, employee_id: int, decisions: list):
    """
    Reanuda el agente después de una interrupción con las decisiones del usuario.

    Args:
        agent: El agente configurado a ejecutar
        conversation_id: ID único de la conversación para mantener contexto
        employee_id: ID del empleado que hace la consulta
        decisions: Lista de decisiones del usuario [{"type": "approve"}, {"type": "reject", "message": "..."}]

    Yields:
        dict: Diccionario con 'type' ('text', 'event', 'interrupt') y 'content'
    """
    import json
    from langgraph.types import Command

    # Configurar el contexto de la conversación (mismo thread_id para reanudar)
    config: RunnableConfig = {"configurable": {"thread_id": conversation_id}}

    try:
        # Reanudar el agente con las decisiones del usuario
        for mode, chunk in agent.stream(
            Command(resume={"decisions": decisions}),
            config=config,
            context=Context(employee_id=employee_id),
            stream_mode=["updates", "messages"],
        ):
            # Modo "messages": tokens del LLM
            if mode == "messages":
                token, metadata = chunk
                
                # Filtrar mensajes de herramientas (ToolMessage)
                message_type = type(token).__name__
                if message_type == "ToolMessage":
                    # No enviar respuestas de herramientas al frontend
                    continue
                
                content_blocks = getattr(token, "content_blocks", [])

                for block in content_blocks:
                    # Solo emitir chunks de texto (ignorar tool_calls)
                    if isinstance(block, dict) and block.get("type") == "text":
                        text_chunk = block.get("text", "")
                        if text_chunk:
                            # Filtro adicional: no enviar si parece ser JSON de herramienta
                            if text_chunk.strip().startswith("{") and (
                                "search_term" in text_chunk or 
                                "project_id" in text_chunk or
                                "found" in text_chunk or
                                "tasks" in text_chunk
                            ):
                                continue
                            
                            yield {"type": "text", "content": text_chunk}

            # Modo "updates": actualizaciones del grafo (incluye interrupciones)
            elif mode == "updates":
                # Detectar interrupciones adicionales (en caso de múltiples herramientas)
                if isinstance(chunk, dict) and "__interrupt__" in chunk:
                    interrupts = chunk["__interrupt__"]
                    
                    if interrupts:
                        # Convertir el objeto Interrupt a dict serializable
                        interrupt_data = []
                        for interrupt in interrupts:
                            if hasattr(interrupt, 'value'):
                                interrupt_data.append(interrupt.value)
                            elif isinstance(interrupt, dict):
                                interrupt_data.append(interrupt)
                        
                        yield {
                            "type": "interrupt",
                            "content": interrupt_data
                        }
                        # IMPORTANTE: Detener el streaming aquí porque la ejecución está pausada
                        return
                
                # Detectar cuando se ejecutan herramientas exitosamente
                for node_name, node_update in chunk.items():
                    if node_name == "tools" and isinstance(node_update, dict):
                        messages = node_update.get("messages", [])
                        for msg in messages:
                            content = getattr(msg, "content", None)
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
        print(f"Error in agent resume stream: {e}")
        raise
