"""
Repositorios abstractos para el módulo de personal_time.

Define los contratos (interfaces) que deben implementar los repositorios
de infraestructura para la sincronización de licencias.
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from app.personal_time.domain.models import TimeOffSyncMapping, TimeOffSyncLog


class TimeOffSyncMappingRepository(ABC):
    """Repositorio abstracto para la tabla de mapeo Humand ↔ Odoo."""

    @abstractmethod
    def save(self, mapping: TimeOffSyncMapping) -> TimeOffSyncMapping:
        """
        Guarda un nuevo mapeo en la base de datos.
        
        Args:
            mapping: Mapeo a guardar
            
        Returns:
            TimeOffSyncMapping: Mapeo guardado con ID asignado
        """
        pass

    @abstractmethod
    def get_by_humand_id(self, humand_request_id: str) -> Optional[TimeOffSyncMapping]:
        """
        Busca un mapeo por el ID de la solicitud en Humand.
        
        Args:
            humand_request_id: ID de la solicitud en Humand
            
        Returns:
            Optional[TimeOffSyncMapping]: Mapeo encontrado o None
        """
        pass

    @abstractmethod
    def get_by_odoo_id(self, odoo_request_id: int) -> Optional[TimeOffSyncMapping]:
        """
        Busca un mapeo por el ID de la solicitud en Odoo.
        
        Args:
            odoo_request_id: ID de la solicitud en Odoo
            
        Returns:
            Optional[TimeOffSyncMapping]: Mapeo encontrado o None
        """
        pass

    @abstractmethod
    def exists_by_humand_id(self, humand_request_id: str) -> bool:
        """
        Verifica si existe un mapeo para una solicitud de Humand.
        
        Args:
            humand_request_id: ID de la solicitud en Humand
            
        Returns:
            bool: True si existe, False en caso contrario
        """
        pass

    @abstractmethod
    def update(self, mapping: TimeOffSyncMapping) -> bool:
        """
        Actualiza un mapeo existente.
        
        Args:
            mapping: Mapeo con datos actualizados (debe tener ID)
            
        Returns:
            bool: True si se actualizó correctamente, False si no existe
        """
        pass

    @abstractmethod
    def get_all_synced(self) -> List[TimeOffSyncMapping]:
        """
        Obtiene todos los mapeos con estado 'synced'.
        
        Returns:
            List[TimeOffSyncMapping]: Lista de mapeos sincronizados
        """
        pass

    @abstractmethod
    def get_all_with_errors(self) -> List[TimeOffSyncMapping]:
        """
        Obtiene todos los mapeos con estado 'error'.
        
        Returns:
            List[TimeOffSyncMapping]: Lista de mapeos con errores
        """
        pass


class TimeOffSyncLogRepository(ABC):
    """Repositorio abstracto para los logs de sincronización."""

    @abstractmethod
    def save(self, log: TimeOffSyncLog) -> TimeOffSyncLog:
        """
        Guarda un nuevo log de sincronización.
        
        Args:
            log: Log a guardar
            
        Returns:
            TimeOffSyncLog: Log guardado con ID asignado
        """
        pass

    @abstractmethod
    def update(self, log: TimeOffSyncLog) -> bool:
        """
        Actualiza un log existente.
        
        Args:
            log: Log con datos actualizados (debe tener ID)
            
        Returns:
            bool: True si se actualizó correctamente, False si no existe
        """
        pass

    @abstractmethod
    def get_last_successful_run(self) -> Optional[datetime]:
        """
        Obtiene la fecha de la última ejecución exitosa.
        
        Returns:
            Optional[datetime]: Fecha de última ejecución exitosa o None
        """
        pass

    @abstractmethod
    def get_by_id(self, log_id: int) -> Optional[TimeOffSyncLog]:
        """
        Busca un log por su ID.
        
        Args:
            log_id: ID del log
            
        Returns:
            Optional[TimeOffSyncLog]: Log encontrado o None
        """
        pass

    @abstractmethod
    def get_recent_logs(self, limit: int = 10) -> List[TimeOffSyncLog]:
        """
        Obtiene los logs más recientes.
        
        Args:
            limit: Número máximo de logs a retornar
            
        Returns:
            List[TimeOffSyncLog]: Lista de logs ordenados por fecha descendente
        """
        pass

    @abstractmethod
    def get_all_by_status(self, status: str) -> List[TimeOffSyncLog]:
        """
        Obtiene todos los logs con un estado específico.
        
        Args:
            status: Estado a filtrar (running, success, error, partial_success)
            
        Returns:
            List[TimeOffSyncLog]: Lista de logs con el estado especificado
        """
        pass
