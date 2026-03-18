from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List, Dict, Any


class SyncedRecordDetail(BaseModel):
    """Detalle de un registro nuevo sincronizado exitosamente a Odoo."""

    humand_request_id: str
    odoo_request_id: int
    employee_name: str
    employee_email: str
    policy_type: str
    from_date: date
    to_date: date
    humand_state: str
    odoo_state: str


class StatusUpdateRecordDetail(BaseModel):
    """Detalle de un registro cuyo estado fue actualizado en Odoo."""

    humand_request_id: str
    odoo_request_id: int
    employee_name: str
    employee_email: str
    policy_type: str
    from_date: date
    to_date: date
    previous_odoo_state: str
    new_odoo_state: str
    humand_state: str


class SkippedRecordDetail(BaseModel):
    """Detalle de un registro que fue omitido durante el procesamiento."""

    humand_request_id: str
    reason: str


class ErrorRecordDetail(BaseModel):
    """Detalle estructurado de un error ocurrido durante el procesamiento."""

    humand_request_id: str
    error_message: str
    error_type: Optional[str] = None
    employee_name: Optional[str] = None
    employee_email: Optional[str] = None
    policy_type: Optional[str] = None


class NewRequestsPhaseDetail(BaseModel):
    """Detalle completo de la fase de sincronización de nuevas solicitudes."""

    total_processed: int = 0
    successfully_synced: int = 0
    skipped: int = 0
    errors_count: int = 0
    synced_records: List[SyncedRecordDetail] = Field(default_factory=list)
    skipped_records: List[SkippedRecordDetail] = Field(default_factory=list)
    errors: List[ErrorRecordDetail] = Field(default_factory=list)


class StatusUpdatesPhaseDetail(BaseModel):
    """Detalle completo de la fase de sincronización de estados."""

    total_processed: int = 0
    status_updates_count: int = 0
    skipped: int = 0
    errors_count: int = 0
    updated_records: List[StatusUpdateRecordDetail] = Field(default_factory=list)
    skipped_records: List[SkippedRecordDetail] = Field(default_factory=list)
    errors: List[ErrorRecordDetail] = Field(default_factory=list)


class SyncSummary(BaseModel):
    """Resumen general de la ejecución de sincronización."""

    total_processed: int = 0
    total_synced: int = 0
    total_errors: int = 0


class RunDetails(BaseModel):
    """Detalles completos de una ejecución de sincronización."""

    new_requests: NewRequestsPhaseDetail = Field(default_factory=NewRequestsPhaseDetail)
    status_updates: StatusUpdatesPhaseDetail = Field(default_factory=StatusUpdatesPhaseDetail)
    summary: SyncSummary = Field(default_factory=SyncSummary)


class SyncRunResponse(BaseModel):
    """Schema de respuesta para el endpoint de sincronización."""

    run_id: int = Field(..., description="ID de la ejecución del job")
    status: str = Field(..., description="Estado de la ejecución (success, error, partial_success)")
    message: str = Field(..., description="Mensaje descriptivo del resultado")
    started_at: datetime = Field(..., description="Fecha y hora de inicio de la ejecución")
    finished_at: Optional[datetime] = Field(None, description="Fecha y hora de finalización")
    execution_time_seconds: Optional[float] = Field(None, description="Tiempo de ejecución en segundos")
    new_requests_synced: int = Field(0, description="Cantidad de nuevas solicitudes sincronizadas")
    status_updates_synced: int = Field(0, description="Cantidad de estados actualizados")
    errors_count: int = Field(0, description="Cantidad total de errores")
    run_details: Optional[RunDetails] = Field(None, description="Detalles completos de la ejecución")

    class Config:
        from_attributes = True
