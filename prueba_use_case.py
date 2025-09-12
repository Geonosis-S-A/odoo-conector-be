"""
Script para probar el caso de uso GetDashboardSummaryUseCase
"""

from datetime import date

def main():
    """Función principal para probar el caso de uso."""
    try:
        print("🔄 Iniciando prueba del caso de uso GetDashboardSummaryUseCase...")
        
        # 1. Conectar a Odoo
        from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
        odoo_connection = get_odoo_connection()
        print("✅ Conexión a Odoo establecida")
        
        # 2. Crear instancia del gateway
        from app.dashboard.infra.repositories import OdooDashboardDataGateway
        dashboard_gateway = OdooDashboardDataGateway(odoo_connection)
        print("✅ Gateway de dashboard creado")
        
        # 3. Crear instancia del caso de uso
        from app.dashboard.application.use_cases.get_dashboard_summary import GetDashboardSummaryUseCase
        use_case = GetDashboardSummaryUseCase(dashboard_gateway)
        print("✅ Caso de uso creado")
        
        # 4. Definir parámetros de prueba (usar los mismos que funcionaron en prueba.py)
        user_id = 1
        date_from = date(2025, 9, 1)
        date_to = date(2025, 9, 9)
        
        print(f"\n📊 Ejecutando caso de uso...")
        print(f"   Usuario ID: {user_id}")
        print(f"   Período: {date_from} a {date_to}")
        print()
        
        # 5. Ejecutar caso de uso
        dashboard_summary = use_case.execute(user_id, date_from, date_to)
        
        # 6. Mostrar resultados
        print(f"\n📈 Resumen del Dashboard:")
        print(f"   Meta - Usuarios en equipo: {dashboard_summary.meta['users_count']}")
        print(f"   Summary - Horas período: total={dashboard_summary.summary['hours_selected_period'].total}, promedio={dashboard_summary.summary['hours_selected_period'].average_per_user}")
        print(f"   Summary - Entradas período: total={dashboard_summary.summary['entries_selected_period'].total}, promedio={dashboard_summary.summary['entries_selected_period'].average_per_user}")
        print(f"   Summary - Promedio diario: total={dashboard_summary.summary['daily_average_hours'].total}, promedio={dashboard_summary.summary['daily_average_hours'].average_per_user}, unidad={dashboard_summary.summary['daily_average_hours'].unit}")
        print(f"   Totales - Por proyecto: {len(dashboard_summary.totals['by_project'])} proyectos")
        print(f"   Totales - Por tarea: {len(dashboard_summary.totals['by_task'])} tareas") 
        print(f"   Totales - Por empleado: {len(dashboard_summary.totals['by_employee'])} empleados")
        
        print(f"\n✅ Caso de uso ejecutado exitosamente!")
        
        return dashboard_summary
        
    except Exception as e:
        print(f"❌ Error durante la prueba del caso de uso: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
