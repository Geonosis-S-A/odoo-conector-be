from agent.core.agent import create_timesheet_agent, run_agent_stream

# Crear una instancia global del agente (se reutiliza entre llamadas)
_agent = None
_checkpointer = None

def get_agent():
    """Obtiene o crea la instancia del agente (patrón singleton)."""
    global _agent, _checkpointer
    if _agent is None:
        _agent, _checkpointer = create_timesheet_agent()
    return _agent

def run_agent_service(prompt: str, conversation_id: str, employee_id: int):
    """
    Ejecuta el agente con streaming y genera chunks de la respuesta en tiempo real.
    
    Args:
        prompt: Mensaje del usuario
        conversation_id: ID único de la conversación para mantener contexto
        employee_id: ID del empleado que hace la consulta
    
    Yields:
        str: Chunks de texto de la respuesta del agente
    """
    # Obtener el agente (se crea solo la primera vez)
    agent = get_agent()
    
    # Ejecutar el agente con streaming
    for chunk in run_agent_stream(agent, prompt, conversation_id, employee_id):
        yield chunk