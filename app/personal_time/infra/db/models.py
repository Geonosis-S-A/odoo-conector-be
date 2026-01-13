"""
Modelos de base de datos para sincronización de tiempo personal entre Humand y Odoo.
"""
from datetime import datetime, UTC
from typing import Optional
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import String, event, UniqueConstraint, Index, JSON as JSONType


class TimeOffSyncMappingModel(SQLModel, table=True):
    """
    Tabla de mapeo (Bridge Table) para relacionar IDs de Humand con IDs de Odoo.
    
    Esta tabla permite rastrear qué solicitud de licencia en Humand corresponde
    a qué solicitud en Odoo, facilitando las actualizaciones posteriores.
    """
    __tablename__ = "timeoff_sync_mapping"  # type: ignore
    __table_args__ = (
        UniqueConstraint("humand_request_id", name="uq_humand_request_id"),
        Index("ix_humand_request_id", "humand_request_id"),
        Index("ix_odoo_request_id", "odoo_request_id"),
    )
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # ID de la solicitud en Humand (fuente de verdad)
    humand_request_id: str = Field(
        sa_column=Column(String(255), nullable=False)
    )
    
    # ID de la solicitud creada en Odoo
    odoo_request_id: int
    
    # Email del usuario en Humand
    humand_user_email: str = Field(
        sa_column=Column(String(255), nullable=False)
    )
    
    # ID del empleado en Odoo
    odoo_employee_id: int
    
    # Estado de la sincronización
    sync_status: str = Field(
        default="synced",
        sa_column=Column(String(50), nullable=False)
    )  # synced, error, pending
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Metadata adicional
    last_sync_error: Optional[str] = Field(
        default=None,
        sa_column=Column(String(1000), nullable=True)
    )


class TimeOffSyncLogModel(SQLModel, table=True):
    """
    Tabla para registrar las ejecuciones del job de sincronización.
    
    Mantiene un historial de cada ejecución del cron job, incluyendo el estado,
    fecha de ejecución, y métricas de sincronización.
    """
    __tablename__ = "timeoff_sync_log"  # type: ignore
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Fecha de inicio de la ejecución del job
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    
    # Fecha de finalización de la ejecución
    finished_at: Optional[datetime] = Field(default=None)
    
    # Estado de la ejecución
    status: str = Field(
        default="running",
        sa_column=Column(String(50), nullable=False)
    )  # running, success, error, partial_success
    
    # Fecha del último job exitoso (para filtrado en próxima ejecución)
    last_successful_run: Optional[datetime] = Field(default=None)
    
    # Métricas de la sincronización
    new_requests_synced: int = Field(default=0)  # Nuevas licencias creadas
    status_updates_synced: int = Field(default=0)  # Estados actualizados
    errors_count: int = Field(default=0)  # Cantidad de errores
    
    # Mensajes y errores
    error_message: Optional[str] = Field(
        default=None,
        sa_column=Column(String(2000), nullable=True)
    )
    
    # Metadata adicional
    execution_time_seconds: Optional[float] = Field(default=None)
    
    # Detalles completos de la ejecución en formato JSON
    run_details: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSONType, nullable=True)
    )


# Event listeners para actualizar automáticamente el campo updated_at
@event.listens_for(TimeOffSyncMappingModel, "before_update")
def update_mapping_timestamp(mapper, connection, target):
    """Actualiza el timestamp cuando se modifica un registro de mapeo."""
    target.updated_at = datetime.now(UTC)

