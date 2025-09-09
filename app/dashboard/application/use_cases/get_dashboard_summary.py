from datetime import date
from typing import List

from app.dashboard.domain.models import (
    DashboardSummary,
    KPI,
    ProjectTotal,
    TaskTotal,
    EmployeeTotal,
)
from app.dashboard.domain.repositories import DashboardDataGateway
from app.timesheet_line.domain.models import DetailedTimesheetLine


class GetDashboardSummaryUseCase:
    """Caso de uso para obtener el resumen del dashboard del equipo."""

    def __init__(self, dashboard_gateway: DashboardDataGateway):
        self.dashboard_gateway = dashboard_gateway

    def execute(self, user_id: int, date_from: date, date_to: date) -> DashboardSummary:
        """
        Ejecuta el caso de uso para obtener el resumen del dashboard.
        
        Args:
            user_id: ID del usuario que solicita el dashboard
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            
        Returns:
            DashboardSummary con todos los KPIs y totales calculados
        """
        print(f"🔄 GetDashboardSummaryUseCase.execute iniciado")
        print(f"   user_id: {user_id}")
        print(f"   período: {date_from} a {date_to}")

        # 1. Obtener datos de timesheet del equipo
        timesheet_data = self.dashboard_gateway.get_team_timesheet_data(
            user_id, date_from, date_to
        )
        print(f"📊 Datos de timesheet obtenidos: {len(timesheet_data)} registros")

        # 2. Obtener cantidad de usuarios del equipo
        users_count = self.dashboard_gateway.get_active_team_users_count(user_id)
        print(f"👥 Usuarios en el equipo: {users_count}")

        # 3. Por ahora, crear KPIs dummy para verificar que todo funciona
        hours_kpi = KPI(total=0.0, average_per_user=0.0)
        entries_kpi = KPI(total=0.0, average_per_user=0.0)
        daily_average_kpi = KPI(total=0.0, average_per_user=0.0, unit="hours/day")

        # 4. Por ahora, crear listas vacías para los totales
        by_project: List[ProjectTotal] = []
        by_task: List[TaskTotal] = []
        by_employee: List[EmployeeTotal] = []

        # 5. Mostrar información de debug sobre los datos recibidos
        if timesheet_data:
            print(f"📋 Primeros 3 registros recibidos:")
            for i, record in enumerate(timesheet_data[:3]):
                print(f"   {i+1}. Proyecto: {record.project.name}")
                print(f"      Empleado: {record.employee_id}")
                print(f"      Horas: {record.hours}")
                print(f"      Fecha: {record.date}")
                print(f"      Tarea: {record.task.name if record.task else 'Sin tarea'}")
                print()

        # 6. Crear y retornar el resumen del dashboard
        dashboard_summary = DashboardSummary.create(
            users_count=users_count,
            hours_selected_period=hours_kpi,
            entries_selected_period=entries_kpi,
            daily_average_hours=daily_average_kpi,
            by_project=by_project,
            by_task=by_task,
            by_employee=by_employee,
        )

        print(f"✅ DashboardSummary creado exitosamente")
        return dashboard_summary
