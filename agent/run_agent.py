from agent.core.agent import create_timesheet_agent, run_agent_stream
import sys

def print_separator():
    """Imprime un separador visual."""
    print("\n" + "="*80 + "\n")

def print_welcome():
    """Imprime mensaje de bienvenida."""
    print_separator()
    print("🎯 AGENTE DE TIMESHEETS - Modo Interactivo")
    print("\nComandos disponibles:")
    print("  - Escribe tu mensaje para interactuar con el agente")
    print("  - 'salir', 'exit', 'quit' para terminar")
    print("  - 'limpiar', 'clear' para limpiar la pantalla")
    print_separator()

def run_interactive_agent():
    """Ejecuta el agente en modo interactivo."""
    print_welcome()
    
    # Crear el agente una sola vez
    print("🔧 Inicializando agente...")
    agent, checkpointer = create_timesheet_agent()
    conversation_id = "interactive_session_1"
    employee_id = 617  # ID de prueba
    print("✅ Agente listo\n")
    
    while True:
        try:
            # Solicitar input al usuario
            user_input = input("👤 Tú: ").strip()
            
            # Verificar comandos especiales
            if user_input.lower() in ['salir', 'exit', 'quit', 'q']:
                print("\n👋 ¡Hasta luego! Sesión terminada.")
                break
            
            if user_input.lower() in ['limpiar', 'clear', 'cls']:
                # Limpiar pantalla (compatible con Windows y Unix)
                import os
                os.system('cls' if os.name == 'nt' else 'clear')
                print_welcome()
                continue
            
            # Verificar que el input no esté vacío
            if not user_input:
                print("⚠️  Por favor, escribe un mensaje.")
                continue
            
            # Enviar mensaje al agente con streaming
            print("\n⏳ Procesando...\n")
            print_separator()
            print("🤖 Agente:")
            
            # Procesar stream y mostrar en tiempo real
            full_response = ""
            for chunk in run_agent_stream(agent, user_input, conversation_id, employee_id):
                print(chunk, end='', flush=True)
                full_response += chunk
            
            # Agregar separador final
            print()  # Nueva línea al final
            print_separator()
            
        except KeyboardInterrupt:
            print("\n\n👋 Sesión interrumpida. ¡Hasta luego!")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Intenta de nuevo o escribe 'salir' para terminar.\n")

if __name__ == "__main__":
    run_interactive_agent()