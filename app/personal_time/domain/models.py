# Entidades del dominio para personal_time, desacopladas del ORM

from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class TimeOffType:
    """Representa un tipo de licencia/ausencia en el sistema."""

    id: int
    name: str
    virtual_remaining_leaves: float
    requires_allocation: bool
    has_valid_allocation: bool
    allows_negative: bool

    @classmethod
    def from_odoo_data(cls, odoo_data: dict) -> "TimeOffType":
        """Crea un TimeOffType desde los datos de Odoo.

        Args:
            odoo_data: Diccionario con datos de Odoo que debe contener 'id' y 'name'

        Returns:
            TimeOffType: Instancia del tipo de licencia
        """
        return cls(
            id=odoo_data["id"],
            name=odoo_data["name"],
            virtual_remaining_leaves=odoo_data["virtual_remaining_leaves"],
            requires_allocation=odoo_data["requires_allocation"],
            has_valid_allocation=odoo_data["has_valid_allocation"],
            allows_negative=odoo_data["allows_negative"],
        )


@dataclass
class TimeOffRequest:
    """Representa una solicitud de licencia/ausencia."""

    holiday_status_id: int  # ID del tipo de licencia
    name: Optional[str]  # Descripción/motivo
    request_date_from: date  # Fecha de inicio
    request_date_to: date  # Fecha de fin
    employee_id: int  # ID del empleado
    state: Optional[str] = None  # Estado deseado en Odoo (draft, confirm, validate, refuse, cancel)

    def to_odoo_data(self, include_state: bool = False) -> dict:
        """Convierte la solicitud a formato de Odoo.
        
        Args:
            include_state: Si True, incluye el campo state (solo para referencia, no para create)

        Returns:
            dict: Datos en formato esperado por Odoo hr.leave
        """
        data = {
            "holiday_status_id": self.holiday_status_id,
            "name": self.name or "",
            "request_date_from": self.request_date_from.strftime("%Y-%m-%d"),
            "request_date_to": self.request_date_to.strftime("%Y-%m-%d"),
            "employee_id": self.employee_id,
        }
        
        # NO incluir estado en create() - se debe cambiar después con métodos de acción
        # El estado se guarda en el objeto pero no se pasa a Odoo en el create
        
        return data


@dataclass
class TimeOffRequestResult:
    """Representa el resultado de crear una solicitud de licencia."""

    request_id: Optional[int]
    success: bool
    message: str

    @classmethod
    def success_result(cls, request_id: int) -> "TimeOffRequestResult":
        """Crea un resultado exitoso."""
        return cls(
            request_id=request_id,
            success=True,
            message=f"Solicitud creada exitosamente con ID: {request_id}",
        )

    @classmethod
    def error_result(cls, error_message: str) -> "TimeOffRequestResult":
        """Crea un resultado de error."""
        return cls(
            request_id=None,
            success=False,
            message=f"Error al crear solicitud: {error_message}",
        )


@dataclass
class HumandTimeOffRequest:
    """Representa una solicitud de tiempo personal desde HUMAND."""

    id: str  # ID en HUMAND
    policy_type_id: str
    policy_type_name: str
    user_id: str
    user_email: str
    user_name: str
    from_date: date
    to_date: date
    status: str  # approved, pending, rejected
    days: float
    reason: Optional[str]
    created_at: date
    resolution_date: Optional[date]

    @classmethod
    def from_humand_data(cls, humand_data: dict) -> "HumandTimeOffRequest":
        """Crea un HumandTimeOffRequest desde los datos de HUMAND API.

        Args:
            humand_data: Diccionario con datos de HUMAND API

        Returns:
            HumandTimeOffRequest: Instancia de la solicitud
        """
        # Extraer información del usuario (issuer en la API)
        issuer_data = humand_data.get("issuer", {})
        policy_type_data = humand_data.get("policyType", {})
        
        # Extraer fechas de los objetos from/to
        from_obj = humand_data.get("from", {})
        to_obj = humand_data.get("to", {})
        from_date_str = from_obj.get("date") if isinstance(from_obj, dict) else None
        to_date_str = to_obj.get("date") if isinstance(to_obj, dict) else None
        
        # Fechas de sistema
        created_at_str = humand_data.get("createdAt")
        resolution_date_str = humand_data.get("resolutionDate")
        
        # Construir nombre completo del usuario
        first_name = issuer_data.get("firstName", "")
        last_name = issuer_data.get("lastName", "")
        user_name = f"{first_name} {last_name}".strip()

        return cls(
            id=str(humand_data.get("id", "")),
            policy_type_id=str(policy_type_data.get("id", "")),
            policy_type_name=policy_type_data.get("name", ""),
            user_id=str(issuer_data.get("id", "")),
            user_email=issuer_data.get("email", ""),
            user_name=user_name or issuer_data.get("email", ""),
            from_date=date.fromisoformat(from_date_str) if from_date_str else date.today(),
            to_date=date.fromisoformat(to_date_str) if to_date_str else date.today(),
            status=humand_data.get("state", "pending"),
            days=float(humand_data.get("amountInTime", 0)),
            reason=humand_data.get("description"),
            created_at=date.fromisoformat(created_at_str.split("T")[0]) if created_at_str else date.today(),
            resolution_date=date.fromisoformat(resolution_date_str.split("T")[0]) if resolution_date_str else None,
        )


@dataclass
class TimeOffRequestInfo:
    """Representa información de una solicitud de tiempo personal existente."""

    id: int
    holiday_status_id: int
    holiday_status_name: str
    name: Optional[str]  # Descripción/motivo
    request_date_from: date
    request_date_to: date
    employee_id: int
    employee_name: str
    state: str  # Estado de la solicitud (draft, confirm, validate, refuse, cancel)
    number_of_days: float

    @classmethod
    def from_odoo_data(cls, odoo_data: dict) -> "TimeOffRequestInfo":
        """Crea un TimeOffRequestInfo desde los datos de Odoo.

        Args:
            odoo_data: Diccionario con datos de Odoo hr.leave

        Returns:
            TimeOffRequestInfo: Instancia de la solicitud
        """
        # Manejo de fechas que pueden venir en diferentes formatos
        date_from = odoo_data["request_date_from"]
        date_to = odoo_data["request_date_to"]

        if isinstance(date_from, str):
            date_from = date.fromisoformat(
                date_from.split(" ")[0]
            )  # Tomar solo la fecha si viene con hora

        if isinstance(date_to, str):
            date_to = date.fromisoformat(date_to.split(" ")[0])

        # Manejar campos que pueden ser False en Odoo en lugar de None o cadenas vacías
        def safe_string_value(value, default=""):
            """Convierte valores de Odoo a string, manejando False y None."""
            if value is False or value is None:
                return default
            return str(value)

        # Extraer valores de campos many2one de forma segura
        holiday_status_id = (
            odoo_data["holiday_status_id"][0]
            if isinstance(odoo_data["holiday_status_id"], list)
            else odoo_data["holiday_status_id"]
        )
        holiday_status_name = (
            odoo_data["holiday_status_id"][1]
            if isinstance(odoo_data["holiday_status_id"], list)
            else odoo_data.get("holiday_status_name", "")
        )

        employee_id = (
            odoo_data["employee_id"][0]
            if isinstance(odoo_data["employee_id"], list)
            else odoo_data["employee_id"]
        )
        employee_name = (
            odoo_data["employee_id"][1]
            if isinstance(odoo_data["employee_id"], list)
            else odoo_data.get("employee_name", "")
        )

        return cls(
            id=odoo_data["id"],
            holiday_status_id=holiday_status_id,
            holiday_status_name=safe_string_value(holiday_status_name),
            name=safe_string_value(odoo_data.get("name")),
            request_date_from=date_from,
            request_date_to=date_to,
            employee_id=employee_id,
            employee_name=safe_string_value(employee_name),
            state=safe_string_value(odoo_data.get("state", "draft")),
            number_of_days=float(odoo_data.get("number_of_days", 0)),
        )


@dataclass
class TimeOffSyncMapping:
    """
    Representa el mapeo entre una solicitud de licencia en Humand y Odoo.
    
    Esta entidad del dominio permite rastrear la relación entre los sistemas,
    facilitando las operaciones de sincronización y actualización.
    """
    
    humand_request_id: str  # ID de la solicitud en Humand (fuente de verdad)
    odoo_request_id: int  # ID de la solicitud en Odoo
    humand_user_email: str  # Email del usuario en Humand
    odoo_employee_id: int  # ID del empleado en Odoo
    sync_status: str = "synced"  # Estado: synced, error, pending
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_sync_error: Optional[str] = None
    id: Optional[int] = None  # ID en la base de datos local
    
    @classmethod
    def from_humand_and_odoo(
        cls,
        humand_request: "HumandTimeOffRequest",
        odoo_request_id: int,
        odoo_employee_id: int,
    ) -> "TimeOffSyncMapping":
        """
        Crea un mapeo desde una solicitud de Humand y el ID de Odoo.
        
        Args:
            humand_request: Solicitud desde Humand
            odoo_request_id: ID de la solicitud creada en Odoo
            odoo_employee_id: ID del empleado en Odoo
            
        Returns:
            TimeOffSyncMapping: Nueva instancia del mapeo
        """
        return cls(
            humand_request_id=humand_request.id,
            odoo_request_id=odoo_request_id,
            humand_user_email=humand_request.user_email,
            odoo_employee_id=odoo_employee_id,
            sync_status="synced",
        )


@dataclass
class TimeOffSyncLog:
    """
    Representa un registro de ejecución del job de sincronización.
    
    Esta entidad del dominio mantiene un historial de las ejecuciones,
    permitiendo rastrear éxitos, errores y métricas de sincronización.
    """
    
    started_at: datetime
    status: str = "running"  # running, success, error, partial_success
    finished_at: Optional[datetime] = None
    last_successful_run: Optional[datetime] = None
    new_requests_synced: int = 0
    status_updates_synced: int = 0
    errors_count: int = 0
    error_message: Optional[str] = None
    execution_time_seconds: Optional[float] = None
    id: Optional[int] = None  # ID en la base de datos local
    
    @classmethod
    def create_new_run(cls, last_successful_run: Optional[datetime] = None) -> "TimeOffSyncLog":
        """
        Crea un nuevo log de ejecución.
        
        Args:
            last_successful_run: Fecha de la última ejecución exitosa
            
        Returns:
            TimeOffSyncLog: Nueva instancia del log
        """
        return cls(
            started_at=datetime.now(),
            status="running",
            last_successful_run=last_successful_run,
        )
    
    def mark_as_success(self) -> None:
        """Marca la ejecución como exitosa."""
        self.status = "success"
        self.finished_at = datetime.now()
        if self.started_at:
            self.execution_time_seconds = (self.finished_at - self.started_at).total_seconds()
    
    def mark_as_error(self, error_message: str) -> None:
        """Marca la ejecución como fallida."""
        self.status = "error"
        self.finished_at = datetime.now()
        self.error_message = error_message
        if self.started_at:
            self.execution_time_seconds = (self.finished_at - self.started_at).total_seconds()
    
    def mark_as_partial_success(self) -> None:
        """Marca la ejecución como parcialmente exitosa (con algunos errores)."""
        self.status = "partial_success"
        self.finished_at = datetime.now()
        if self.started_at:
            self.execution_time_seconds = (self.finished_at - self.started_at).total_seconds()
