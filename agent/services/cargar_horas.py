from agent.core.agent import create_timesheet_agent, run_agent_stream

# Crear una instancia global del agente (se reutiliza entre llamadas)
_agent = None
_checkpointer = None

def get_agent():
    """Obtiene o crea la instancia del agente (patrón singleton)."""
    global _agent, _checkpointer
    if _agent is None:
        print("🔄 Agent not initialized, creating new instance...")
        _agent, _checkpointer = create_timesheet_agent()
        print("✅ Agent singleton created")
    else:
        print("♻️  Reusing existing agent instance")
    return _agent

def get_checkpointer():
    """Obtiene la instancia del checkpointer."""
    global _agent, _checkpointer
    if _checkpointer is None:
        # Asegurar que el agente esté inicializado
        get_agent()
    return _checkpointer

def delete_conversation(conversation_id: str) -> dict:
    """
    Elimina una conversación del checkpointer.
    
    Debe llamarse cuando el usuario cierra el diálogo de chat.
    
    Args:
        conversation_id: ID único de la conversación a eliminar
    
    Returns:
        dict: Diccionario con el resultado de la operación
    """
    checkpointer = get_checkpointer()
    
    if checkpointer is None:
        return {
            "success": False,
            "error": "Checkpointer not initialized",
            "message": "Error: El checkpointer no está inicializado"
        }
    
    try:
        deleted_count = checkpointer.delete(conversation_id)
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Conversación {conversation_id} eliminada exitosamente"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Error al eliminar conversación: {str(e)}"
        }

def run_agent_service(prompt: str, conversation_id: str, employee_id: int):
    """
    Ejecuta el agente con streaming y genera chunks de la respuesta en tiempo real.
    
    Args:
        prompt: Mensaje del usuario
        conversation_id: ID único de la conversación para mantener contexto
        employee_id: ID del empleado que hace la consulta
    
    Yields:
        dict: Diccionario con 'type' ('text' o 'event') y 'content'
    """
    print(f"🚀 Starting agent service - conversation_id: {conversation_id}, employee_id: {employee_id}")
    print(f"📨 Prompt: {prompt}")
    
    # Obtener el agente (se crea solo la primera vez)
    print("🔧 Getting agent instance...")
    agent = get_agent()
    print("✅ Agent instance obtained")
    
    # Ejecutar el agente con streaming
    print("▶️  Starting agent stream...")
    chunk_count = 0
    for chunk in run_agent_stream(agent, prompt, conversation_id, employee_id):
        chunk_count += 1
        if chunk_count == 1:
            print(f"📦 First chunk received")
        yield chunk
    
    print(f"✅ Agent stream completed - {chunk_count} chunks sent")