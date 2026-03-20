from typing import List, Optional, Union
from pydantic import BaseModel
from datetime import date


class KPIResponse(BaseModel):
    """Schema de respuesta para un KPI individual."""

    total: float
    average_per_user: float
    unit: Optional[str] = None


class ProjectTotalResponse(BaseModel):
    """Schema de respuesta para totales por proyecto."""

    project_id: int
    project_name: str
    hours: float


class TaskTotalResponse(BaseModel):
    """Schema de respuesta para totales por tarea."""

    task_id: int
    task_name: str
    hours: float
    project_id: int


class EmployeeTotalResponse(BaseModel):
    """Schema de respuesta para totales por empleado."""

    user_id: int
    employee_name: str
    hours: float
    total_cost: Optional[float] = None


class EmployeeWithoutPriceResponse(BaseModel):
    """Schema de respuesta para empleados sin precio configurado."""

    user_id: int
    employee_name: str


class HierarchicalItemResponse(BaseModel):
    """Schema de respuesta para elementos de la estructura jerárquica."""

    type: str  # "project" o "task"
    id: int  # project_id para proyectos, task_id para tareas
    name: str
    total_hours: float
    data: Optional[List["HierarchicalItemResponse"]] = None
    is_artificial: bool = False
    total_cost: Optional[float] = None


class HierarchicalSummaryResponse(BaseModel):
    """Schema de respuesta para el resumen jerárquico."""

    total_hours: float
    data: List[HierarchicalItemResponse]
    total_cost: Optional[float] = None


# Actualizar el modelo de HierarchicalItemResponse para manejar referencias circulares
HierarchicalItemResponse.model_rebuild()


class DashboardSummaryMetaResponse(BaseModel):
    """Schema de respuesta para metadatos del dashboard."""

    users_count: int


class DashboardSummaryMetaResponseByEmployee(DashboardSummaryMetaResponse):
    """Schema de respuesta para metadatos del dashboard."""

    worked_days: int


class DashboardSummaryKPIsResponse(BaseModel):
    """Schema de respuesta para los KPIs del dashboard."""

    hours_selected_period: KPIResponse
    entries_selected_period: KPIResponse
    daily_average_hours: KPIResponse
    total_cost: Optional[KPIResponse] = None


class DashboardSummaryTotalsResponse(BaseModel):
    """Schema de respuesta para los totales desagregados."""

    by_project: List[ProjectTotalResponse]
    by_task: List[TaskTotalResponse]
    by_employee: List[EmployeeTotalResponse]


class DashboardSummaryResponse(BaseModel):
    """Schema de respuesta completo para el resumen del dashboard."""

    meta: DashboardSummaryMetaResponse
    summary: DashboardSummaryKPIsResponse
    totals: DashboardSummaryTotalsResponse
    hierarchical_summary: Optional[HierarchicalSummaryResponse] = None
    employees_without_price: Optional[List[EmployeeWithoutPriceResponse]] = None

    class Config:
        """Configuración del modelo Pydantic."""

        from_attributes = True
        json_encoders = {float: lambda v: round(v, 2) if v is not None else None}


class ValidationStatsResponse(BaseModel):
    """Horas aprobadas y pendientes del período."""

    approved_hours: float
    pending_hours: float


class PreviousPeriodSummaryResponse(BaseModel):
    """KPIs mínimos del período anterior para comparación de tendencias."""

    worked_days: int
    hours_total: float
    entries_total: float
    daily_average: float


class DashboardSummaryResponseByEmployee(BaseModel):
    """Schema de respuesta completo para el resumen del dashboard."""

    meta: DashboardSummaryMetaResponseByEmployee
    summary: DashboardSummaryKPIsResponse
    totals: DashboardSummaryTotalsResponse
    hierarchical_summary: Optional[HierarchicalSummaryResponse] = None
    previous_period: Optional[PreviousPeriodSummaryResponse] = None
    validation_stats: Optional[ValidationStatsResponse] = None

    class Config:
        """Configuración del modelo Pydantic."""

        from_attributes = True
        json_encoders = {float: lambda v: round(v, 2) if v is not None else None}


class ExcelKpiDataResponse(BaseModel):
    """KPI: mismas claves que el endpoint histórico (Proyectos, Horas, Headcount)."""

    proyectos: List[dict]
    horas: List[dict]
    headcount: List[dict]


class ExcelGanttDataResponse(BaseModel):
    """Gantt: hoja Base Gantt (p. ej. pestaña 'base')."""

    base: List[dict]


ExcelDataResponse = Union[ExcelKpiDataResponse, ExcelGanttDataResponse]


class TaskDetailRequest(BaseModel):
    """Schema de request para obtener detalle de empleados por tarea."""

    task_id: Optional[int] = None
    project_id: Optional[int] = None
    date_from: date
    date_to: date


class EmployeeInfoResponse(BaseModel):
    """Schema de respuesta para información del empleado."""

    employee_id: int
    employee_name: str


class SimpleTimesheetLineResponse(BaseModel):
    """Schema de respuesta simplificado para líneas de timesheet."""

    id: int
    name: str
    employee: EmployeeInfoResponse
    hours: float
    date: date
    create_date: Optional[str] = None
    validated: bool
    notification: Optional[dict] = None


class TaskDetailResponse(BaseModel):
    """Schema de respuesta para detalle de empleados por tarea/proyecto."""

    task_id: Optional[int] = None
    project_id: Optional[int] = None
    timesheet_lines: List[SimpleTimesheetLineResponse]
