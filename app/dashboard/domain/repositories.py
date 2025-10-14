from abc import ABC, abstractmethod
from datetime import date
from typing import List, Dict, Any, Optional

from app.dashboard.domain.models import KPI, HierarchicalSummary
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.task.domain.gateway import TaskGateway
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.dashboard.domain.models import ProjectTotal, TaskTotal, EmployeeTotal


class DashboardDataService(ABC):
    """Gateway abstracto para obtener datos necesarios para el dashboard."""

    @abstractmethod
    def get_timesheet_summary(
        self,
        members_ids: list[int],
        date_from: date,
        date_to: date,
        task_gateway: TaskGateway,
        timesheet_line_gateway: TimesheetLineGateway,
        requester_user_id: int | None = None,
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene datos de timesheet del equipo para el período especificado.

        Args:
            members_ids: IDs de los miembros del equipo
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            task_gateway: Gateway de tareas para obtener información de parent_id
            timesheet_line_gateway: Gateway de líneas de timesheet para obtener datos del equipo
            requester_user_id: ID del usuario que solicita el dashboard
        Returns:
            Lista de DetailedTimesheetLine del equipo en el período
        """
        pass

    @abstractmethod
    def calculate_hours_kpi(
        self, timesheet_data: List[DetailedTimesheetLine], users_count: int
    ) -> KPI:
        """Calcula el KPI de horas del período seleccionado."""
        pass

    @abstractmethod
    def calculate_entries_kpi(
        self, timesheet_data: List[DetailedTimesheetLine], users_count: int
    ) -> KPI:
        """Calcula el KPI de entradas del período seleccionado."""
        pass

    @abstractmethod
    def calculate_daily_average_kpi(
        self,
        timesheet_data: List[DetailedTimesheetLine],
        users_count: int,
        date_from: date,
        date_to: date,
    ) -> KPI:
        """Calcula el KPI de promedio diario de horas."""
        pass

    @abstractmethod
    def calculate_project_totals(
        self, timesheet_data: List[DetailedTimesheetLine]
    ) -> List[ProjectTotal]:
        """Calcula los totales de horas por proyecto."""
        pass

    @abstractmethod
    def calculate_task_totals(
        self, timesheet_data: List[DetailedTimesheetLine]
    ) -> List[TaskTotal]:
        """Calcula los totales de horas por tarea."""
        pass

    @abstractmethod
    def calculate_employee_totals(
        self, timesheet_data: List[DetailedTimesheetLine], team_users: List[dict]
    ) -> List[EmployeeTotal]:
        """Calcula los totales de horas por empleado."""
        pass

    @abstractmethod
    def calculate_project_without_task_totals(
        self, project_totals: List[ProjectTotal], task_totals: List[TaskTotal]
    ) -> List[TaskTotal]:
        """
        Calcula las horas cargadas directamente a proyectos sin tarea específica.

        Args:
            project_totals: Lista de totales por proyecto
            task_totals: Lista de totales por tarea

        Returns:
            Lista de ProjectWithoutTaskTotal con las horas cargadas sin tarea
        """
        pass

    @abstractmethod
    def calculate_hierarchical_summary(
        self,
        timesheet_data: List[DetailedTimesheetLine],
        task_gateway: TaskGateway,
        timesheet_costs: Optional[Dict[int, float]] = None,
    ) -> HierarchicalSummary:
        """
        Calcula la estructura jerárquica de proyectos y tareas con casos borde.

        Args:
            timesheet_data: Lista de líneas de timesheet con información detallada
            task_gateway: Gateway de tareas para obtener información de parent_id
            timesheet_costs: Diccionario opcional que mapea timesheet_line_id -> total_cost

        Returns:
            HierarchicalSummary con la estructura anidada completa
        """
        pass

    @abstractmethod
    def get_timesheet_by_task_or_project(
        self,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        timesheet_line_gateway: Optional[TimesheetLineGateway] = None,
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene líneas de timesheet filtradas por tarea o proyecto en un período específico.

        Args:
            task_id: ID de la tarea a filtrar (opcional)
            project_id: ID del proyecto a filtrar (opcional, usado cuando task_id es None)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período
            timesheet_line_gateway: Gateway de líneas de timesheet

        Returns:
            Lista de DetailedTimesheetLine que coinciden con los criterios
        """
        pass
