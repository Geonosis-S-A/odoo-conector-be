# Acá van las entidades propias, desacopladas del ORM SQLModel

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class KPI:
    """Representa un KPI con total y promedio por usuario."""
    total: float
    average_per_user: float
    unit: Optional[str] = None


@dataclass
class ProjectTotal:
    """Representa el total de horas por proyecto."""
    project_id: int
    project_name: str
    hours: float


@dataclass
class TaskTotal:
    """Representa el total de horas por tarea."""
    task_id: int
    task_name: str
    hours: float
    project_id: int


@dataclass
class EmployeeTotal:
    """Representa el total de horas por empleado."""
    user_id: int
    employee_name: str
    hours: float


@dataclass
class DashboardSummary:
    """Modelo principal que contiene toda la información del dashboard."""
    meta: Dict[str, Any]  # {"users_count": int}
    summary: Dict[str, KPI]  # KPIs principales
    totals: Dict[str, List[Any]]  # Totales desagregados

    @classmethod
    def create(
        cls,
        users_count: int,
        hours_selected_period: KPI,
        entries_selected_period: KPI,
        daily_average_hours: KPI,
        by_project: List[ProjectTotal],
        by_task: List[TaskTotal],
        by_employee: List[EmployeeTotal],
    ) -> "DashboardSummary":
        """Factory method para crear un DashboardSummary completo."""
        return cls(
            meta={"users_count": users_count},
            summary={
                "hours_selected_period": hours_selected_period,
                "entries_selected_period": entries_selected_period,
                "daily_average_hours": daily_average_hours,
            },
            totals={
                "by_project": by_project,
                "by_task": by_task,
                "by_employee": by_employee,
            },
        )

@dataclass
class DashboardSummaryByEmployee:
    """Modelo principal que contiene toda la información del dashboard."""
    meta: Dict[str, Any]  # {"users_count": int}
    worked_days: int
    summary: Dict[str, KPI]  # KPIs principales
    totals: Dict[str, List[Any]]  # Totales desagregados

    @classmethod
    def create(
        cls,
        users_count: int,
        worked_days: int,
        hours_selected_period: KPI,
        entries_selected_period: KPI,
        daily_average_hours: KPI,
        by_project: List[ProjectTotal],
        by_task: List[TaskTotal],
        by_employee: List[EmployeeTotal],
    ) -> "DashboardSummaryByEmployee":
        """Factory method para crear un DashboardSummary completo."""
        return cls(
            meta={"users_count": users_count},
            worked_days=worked_days,
            summary={
                "hours_selected_period": hours_selected_period,
                "entries_selected_period": entries_selected_period,
                "daily_average_hours": daily_average_hours,
            },
            totals={
                "by_project": by_project,
                "by_task": by_task,
                "by_employee": by_employee,
            },
        )
