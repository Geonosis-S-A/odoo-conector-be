"""
Implementaciones concretas de los repositorios usando SQLModel.

Estas implementaciones se conectan con la base de datos y realizan
las operaciones CRUD necesarias para la sincronización.
"""
from typing import Optional, List
from datetime import datetime
from sqlmodel import select, Session

from app.personal_time.domain.repositories import (
    TimeOffSyncMappingRepository,
    TimeOffSyncLogRepository,
)
from app.personal_time.domain.models import TimeOffSyncMapping, TimeOffSyncLog
from app.personal_time.infra.db.models import (
    TimeOffSyncMappingModel,
    TimeOffSyncLogModel,
)


class SQLModelTimeOffSyncMappingRepository(TimeOffSyncMappingRepository):
    """Implementación del repositorio de mapeo usando SQLModel."""

    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            db: Sesión de SQLModel
        """
        self.db = db

    def _model_to_domain(self, model: TimeOffSyncMappingModel) -> TimeOffSyncMapping:
        """Convierte un modelo de DB a entidad de dominio."""
        return TimeOffSyncMapping(
            id=model.id,
            humand_request_id=model.humand_request_id,
            odoo_request_id=model.odoo_request_id,
            humand_user_email=model.humand_user_email,
            odoo_employee_id=model.odoo_employee_id,
            sync_status=model.sync_status,
            created_at=model.created_at,
            updated_at=model.updated_at,
            last_sync_error=model.last_sync_error,
        )

    def _domain_to_model(self, domain: TimeOffSyncMapping) -> TimeOffSyncMappingModel:
        """Convierte una entidad de dominio a modelo de DB."""
        return TimeOffSyncMappingModel(
            id=domain.id,
            humand_request_id=domain.humand_request_id,
            odoo_request_id=domain.odoo_request_id,
            humand_user_email=domain.humand_user_email,
            odoo_employee_id=domain.odoo_employee_id,
            sync_status=domain.sync_status,
            created_at=domain.created_at or datetime.now(),
            updated_at=domain.updated_at or datetime.now(),
            last_sync_error=domain.last_sync_error,
        )

    def save(self, mapping: TimeOffSyncMapping) -> TimeOffSyncMapping:
        """Guarda un nuevo mapeo en la base de datos."""
        model = self._domain_to_model(mapping)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_domain(model)

    def get_by_humand_id(self, humand_request_id: str) -> Optional[TimeOffSyncMapping]:
        """Busca un mapeo por el ID de la solicitud en Humand."""
        statement = select(TimeOffSyncMappingModel).where(
            TimeOffSyncMappingModel.humand_request_id == humand_request_id
        )
        model = self.db.exec(statement).first()
        return self._model_to_domain(model) if model else None

    def get_by_odoo_id(self, odoo_request_id: int) -> Optional[TimeOffSyncMapping]:
        """Busca un mapeo por el ID de la solicitud en Odoo."""
        statement = select(TimeOffSyncMappingModel).where(
            TimeOffSyncMappingModel.odoo_request_id == odoo_request_id
        )
        model = self.db.exec(statement).first()
        return self._model_to_domain(model) if model else None

    def exists_by_humand_id(self, humand_request_id: str) -> bool:
        """Verifica si existe un mapeo para una solicitud de Humand."""
        statement = select(TimeOffSyncMappingModel).where(
            TimeOffSyncMappingModel.humand_request_id == humand_request_id
        )
        result = self.db.exec(statement).first()
        return result is not None

    def update(self, mapping: TimeOffSyncMapping) -> bool:
        """Actualiza un mapeo existente."""
        if not mapping.id:
            return False

        statement = select(TimeOffSyncMappingModel).where(
            TimeOffSyncMappingModel.id == mapping.id
        )
        model = self.db.exec(statement).first()
        
        if not model:
            return False

        # Actualizar campos
        model.humand_request_id = mapping.humand_request_id
        model.odoo_request_id = mapping.odoo_request_id
        model.humand_user_email = mapping.humand_user_email
        model.odoo_employee_id = mapping.odoo_employee_id
        model.sync_status = mapping.sync_status
        model.last_sync_error = mapping.last_sync_error
        # updated_at se actualiza automáticamente por el event listener

        self.db.commit()
        self.db.refresh(model)
        return True

    def get_all_synced(self) -> List[TimeOffSyncMapping]:
        """Obtiene todos los mapeos con estado 'synced'."""
        statement = select(TimeOffSyncMappingModel).where(
            TimeOffSyncMappingModel.sync_status == "synced"
        )
        models = self.db.exec(statement).all()
        return [self._model_to_domain(model) for model in models]

    def get_all_with_errors(self) -> List[TimeOffSyncMapping]:
        """Obtiene todos los mapeos con estado 'error'."""
        statement = select(TimeOffSyncMappingModel).where(
            TimeOffSyncMappingModel.sync_status == "error"
        )
        models = self.db.exec(statement).all()
        return [self._model_to_domain(model) for model in models]


class SQLModelTimeOffSyncLogRepository(TimeOffSyncLogRepository):
    """Implementación del repositorio de logs usando SQLModel."""

    def __init__(self, db: Session):
        """
        Inicializa el repositorio con una sesión de base de datos.
        
        Args:
            db: Sesión de SQLModel
        """
        self.db = db

    def _model_to_domain(self, model: TimeOffSyncLogModel) -> TimeOffSyncLog:
        """Convierte un modelo de DB a entidad de dominio."""
        return TimeOffSyncLog(
            id=model.id,
            started_at=model.started_at,
            finished_at=model.finished_at,
            status=model.status,
            last_successful_run=model.last_successful_run,
            new_requests_synced=model.new_requests_synced,
            status_updates_synced=model.status_updates_synced,
            errors_count=model.errors_count,
            error_message=model.error_message,
            execution_time_seconds=model.execution_time_seconds,
            run_details=model.run_details,
        )

    def _domain_to_model(self, domain: TimeOffSyncLog) -> TimeOffSyncLogModel:
        """Convierte una entidad de dominio a modelo de DB."""
        return TimeOffSyncLogModel(
            id=domain.id,
            started_at=domain.started_at,
            finished_at=domain.finished_at,
            status=domain.status,
            last_successful_run=domain.last_successful_run,
            new_requests_synced=domain.new_requests_synced,
            status_updates_synced=domain.status_updates_synced,
            errors_count=domain.errors_count,
            error_message=domain.error_message,
            execution_time_seconds=domain.execution_time_seconds,
            run_details=domain.run_details,
        )

    def save(self, log: TimeOffSyncLog) -> TimeOffSyncLog:
        """Guarda un nuevo log de sincronización."""
        model = self._domain_to_model(log)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return self._model_to_domain(model)

    def update(self, log: TimeOffSyncLog) -> bool:
        """Actualiza un log existente."""
        if not log.id:
            return False

        statement = select(TimeOffSyncLogModel).where(TimeOffSyncLogModel.id == log.id)
        model = self.db.exec(statement).first()
        
        if not model:
            return False

        # Actualizar campos
        model.finished_at = log.finished_at
        model.status = log.status
        model.last_successful_run = log.last_successful_run
        model.new_requests_synced = log.new_requests_synced
        model.status_updates_synced = log.status_updates_synced
        model.errors_count = log.errors_count
        model.error_message = log.error_message
        model.execution_time_seconds = log.execution_time_seconds
        model.run_details = log.run_details

        self.db.commit()
        self.db.refresh(model)
        return True

    def get_last_successful_run(self) -> Optional[datetime]:
        """Obtiene la fecha de la última ejecución exitosa."""
        statement = (
            select(TimeOffSyncLogModel)
            .where(TimeOffSyncLogModel.status == "success")
            .order_by(TimeOffSyncLogModel.started_at.desc())  # type: ignore
        )
        model = self.db.exec(statement).first()
        return model.started_at if model else datetime.now()

    def get_by_id(self, log_id: int) -> Optional[TimeOffSyncLog]:
        """Busca un log por su ID."""
        statement = select(TimeOffSyncLogModel).where(TimeOffSyncLogModel.id == log_id)
        model = self.db.exec(statement).first()
        return self._model_to_domain(model) if model else None

    def get_recent_logs(self, limit: int = 10) -> List[TimeOffSyncLog]:
        """Obtiene los logs más recientes."""
        statement = (
            select(TimeOffSyncLogModel)
            .order_by(TimeOffSyncLogModel.started_at.desc())  # type: ignore
            .limit(limit)
        )
        models = self.db.exec(statement).all()
        return [self._model_to_domain(model) for model in models]

    def get_all_by_status(self, status: str) -> List[TimeOffSyncLog]:
        """Obtiene todos los logs con un estado específico."""
        statement = select(TimeOffSyncLogModel).where(
            TimeOffSyncLogModel.status == status
        )
        models = self.db.exec(statement).all()
        return [self._model_to_domain(model) for model in models]
