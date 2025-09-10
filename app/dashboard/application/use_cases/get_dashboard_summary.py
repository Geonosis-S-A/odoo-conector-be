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
from app.users.domain.repositories import EmployeeGateway
from app.task.domain.gateway import TaskGateway


class GetDashboardSummaryUseCase:
    """Caso de uso para obtener el resumen del dashboard del equipo."""

    def __init__(self, dashboard_gateway: DashboardDataGateway, employee_gateway: EmployeeGateway, task_gateway: TaskGateway):
        self.dashboard_gateway = dashboard_gateway
        self.employee_gateway = employee_gateway
        self.task_gateway = task_gateway

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

        # 1. Obtener datos de timesheet del equipo
        timesheet_data = self.dashboard_gateway.get_team_timesheet_data(
            user_id, date_from, date_to, self.task_gateway
        )

        # 2. Obtener cantidad de usuarios del equipo
        users_count = self.dashboard_gateway.get_active_team_users_count(user_id)

        # 3. Calcular KPIs reales
        hours_kpi = self._calculate_hours_kpi(timesheet_data, users_count)
        entries_kpi = self._calculate_entries_kpi(timesheet_data, users_count)
        daily_average_kpi = self._calculate_daily_average_kpi(timesheet_data, users_count, date_from, date_to)

        # 4. Calcular totales desagregados
        by_project = self._calculate_project_totals(timesheet_data)
        by_task = self._calculate_task_totals(timesheet_data)
        by_employee = self._calculate_employee_totals(timesheet_data)

        # 5. Crear y retornar el resumen del dashboard
        dashboard_summary = DashboardSummary.create(
            users_count=users_count,
            hours_selected_period=hours_kpi,
            entries_selected_period=entries_kpi,
            daily_average_hours=daily_average_kpi,
            by_project=by_project,
            by_task=by_task,
            by_employee=by_employee,
        )


        return dashboard_summary

    def _calculate_hours_kpi(self, timesheet_data: List[DetailedTimesheetLine], users_count: int) -> KPI:
        """Calcula el KPI de horas del período seleccionado."""
        total_hours = sum(record.hours for record in timesheet_data)
        average_per_user = total_hours / users_count if users_count > 0 else 0.0
        
        return KPI(total=total_hours, average_per_user=average_per_user)

    def _calculate_entries_kpi(self, timesheet_data: List[DetailedTimesheetLine], users_count: int) -> KPI:
        """Calcula el KPI de entradas del período seleccionado."""
        total_entries = len(timesheet_data)
        average_per_user = total_entries / users_count if users_count > 0 else 0.0
        
        return KPI(total=float(total_entries), average_per_user=average_per_user)

    def _calculate_daily_average_kpi(
        self, 
        timesheet_data: List[DetailedTimesheetLine], 
        users_count: int, 
        date_from: date, 
        date_to: date
    ) -> KPI:
        """Calcula el KPI de promedio diario de horas."""
        total_hours = sum(record.hours for record in timesheet_data)
        days_in_period = (date_to - date_from).days + 1
        
        total_daily_average = total_hours / days_in_period if days_in_period > 0 else 0.0
        average_per_user = total_daily_average / users_count if users_count > 0 else 0.0
        
        return KPI(total=total_daily_average, average_per_user=average_per_user, unit="hours/day")

    def _calculate_project_totals(self, timesheet_data: List[DetailedTimesheetLine]) -> List[ProjectTotal]:
        """Calcula totales de horas por proyecto."""
        project_totals = {}
        
        for record in timesheet_data:
            project_id = record.project.id
            if project_id not in project_totals:
                project_totals[project_id] = {
                    "name": record.project.name,
                    "hours": 0.0
                }
            project_totals[project_id]["hours"] += record.hours
        
        # Convertir a lista de ProjectTotal ordenada por horas (mayor a menor)
        project_list = [
            ProjectTotal(
                project_id=project_id,
                project_name=data["name"],
                hours=data["hours"]
            )
            for project_id, data in project_totals.items()
        ]
        
        project_list.sort(key=lambda x: x.hours, reverse=True)
        
            
        return project_list

    def _calculate_task_totals(self, timesheet_data: List[DetailedTimesheetLine]) -> List[TaskTotal]:
        """Calcula totales de horas por tarea (solo tareas principales, ignora subtareas)."""
        task_totals = {}
        
        for record in timesheet_data:
            # Solo procesar si tiene tarea
            if record.task:
                task_id = record.task.id
                # Aquí podríamos filtrar subtareas si fuera necesario
                # Por ahora incluimos todas las tareas
                if task_id not in task_totals:
                    task_totals[task_id] = {
                        "name": record.task.name,
                        "hours": 0.0,
                        "project_id": record.task.project_id
                    }
                task_totals[task_id]["hours"] += record.hours
        
        # Convertir a lista de TaskTotal ordenada por horas (mayor a menor)
        task_list = [
            TaskTotal(
                task_id=task_id,
                task_name=data["name"],
                hours=data["hours"],
                project_id=data["project_id"]
            )
            for task_id, data in task_totals.items()
        ]
        
        task_list.sort(key=lambda x: x.hours, reverse=True)
        
            
        return task_list

    def _calculate_employee_totals(self, timesheet_data: List[DetailedTimesheetLine]) -> List[EmployeeTotal]:
        """Calcula totales de horas por empleado con nombres obtenidos de Odoo."""
        employee_totals = {}
        
        # Agrupar horas por empleado
        for record in timesheet_data:
            employee_id = record.employee_id
            if employee_id not in employee_totals:
                employee_totals[employee_id] = 0.0
            employee_totals[employee_id] += record.hours
        
        # Obtener nombres de empleados desde Odoo
        employee_names = self._get_employee_names(list(employee_totals.keys()))
        
        # Crear lista de EmployeeTotal
        employee_list = [
            EmployeeTotal(
                user_id=employee_id,
                employee_name=employee_names.get(employee_id, f"Empleado {employee_id}"),
                hours=hours
            )
            for employee_id, hours in employee_totals.items()
        ]
        
        employee_list.sort(key=lambda x: x.hours, reverse=True)
        
            
        return employee_list

    def _get_employee_names(self, employee_ids: List[int]) -> dict:
        """Obtiene los nombres de los empleados desde Odoo usando el EmployeeGateway."""
        try:
            employee_names = {}
            
            # Si no hay empleados, retornar diccionario vacío
            if not employee_ids:
                return employee_names
            
            # Obtener información de cada empleado usando el gateway
            for employee_id in employee_ids:
                employee = self.employee_gateway.get_by_id(employee_id)
                if employee:
                    employee_names[employee_id] = employee.full_name
                else:
                    # Si no se encuentra el empleado, usar nombre genérico
                    employee_names[employee_id] = f"Empleado {employee_id}"
            
            return employee_names
            
        except Exception as e:
            # En caso de error, retornar nombres genéricos
            return {emp_id: f"Empleado {emp_id}" for emp_id in employee_ids}
