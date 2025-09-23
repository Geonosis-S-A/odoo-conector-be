from datetime import date
from typing import Optional
from app.personal_time.domain.gateway import TimeOffGateway
from app.personal_time.domain.models import TimeOffRequest, TimeOffRequestResult


class UpdateTimeOffRequestUseCase:
    """Caso de uso para actualizar una solicitud de tiempo personal existente."""

    def __init__(self, timeoff_gateway: TimeOffGateway):
        """Inicializa el caso de uso con el gateway de tipos de licencias.

        Args:
            timeoff_gateway: Gateway para acceder a las operaciones de licencias
        """
        self.timeoff_gateway = timeoff_gateway

    def execute(
        self,
        request_id: int,
        employee_id: int,
        holiday_status_id: int,
        request_date_from: date,
        request_date_to: date,
        description: Optional[str] = None,
    ) -> TimeOffRequestResult:
        """Ejecuta el caso de uso para actualizar una solicitud de tiempo personal existente.

        Args:
            request_id: ID de la solicitud a actualizar
            employee_id: ID del empleado que solicita la licencia
            holiday_status_id: ID del tipo de licencia
            request_date_from: Fecha de inicio de la licencia
            request_date_to: Fecha de fin de la licencia
            description: Descripción/motivo de la solicitud

        Returns:
            TimeOffRequestResult: Resultado de la operación de actualización

        Raises:
            ValueError: Si los parámetros no son válidos
            Exception: Si hay un error al actualizar la solicitud
        """
        # Validaciones de negocio
        self._validate_input_parameters(
            request_id,
            employee_id,
            holiday_status_id,
            request_date_from,
            request_date_to,
            description,
        )

        timeoff_request_state = self.timeoff_gateway.get_timeoff_request_state(
            request_id
        )
        if timeoff_request_state != "confirm" and timeoff_request_state != "draft":
            raise ValueError("La solicitud no está en estado confirm o draft")

        # Crear la solicitud actualizada
        timeoff_request = TimeOffRequest(
            holiday_status_id=holiday_status_id,
            name=description,
            request_date_from=request_date_from,
            request_date_to=request_date_to,
            employee_id=employee_id,
        )

        # Delegar al gateway - cualquier error se propaga directamente
        return self.timeoff_gateway.update_timeoff_request(request_id, timeoff_request)

    def _validate_input_parameters(
        self,
        request_id: int,
        employee_id: int,
        holiday_status_id: int,
        request_date_from: date,
        request_date_to: date,
        description: Optional[str],
    ) -> None:
        """Valida los parámetros de entrada.

        Args:
            request_id: ID de la solicitud a actualizar
            employee_id: ID del empleado
            holiday_status_id: ID del tipo de licencia
            request_date_from: Fecha de inicio
            request_date_to: Fecha de fin
            description: Descripción

        Raises:
            ValueError: Si algún parámetro no es válido
        """
        # Validar ID de solicitud
        if not isinstance(request_id, int) or request_id <= 0:
            raise ValueError("request_id debe ser un entero positivo")

        # Validar IDs
        if not isinstance(employee_id, int) or employee_id <= 0:
            raise ValueError("employee_id debe ser un entero positivo")

        if not isinstance(holiday_status_id, int) or holiday_status_id <= 0:
            raise ValueError("holiday_status_id debe ser un entero positivo")

        # Validar fechas
        if not isinstance(request_date_from, date):
            raise ValueError("request_date_from debe ser una fecha válida")

        if not isinstance(request_date_to, date):
            raise ValueError("request_date_to debe ser una fecha válida")

        if request_date_from > request_date_to:
            raise ValueError(
                "La fecha de inicio no puede ser posterior a la fecha de fin"
            )

        if description and not description.strip():
            raise ValueError("description no puede estar vacía")

        if description and len(description.strip()) > 500:
            raise ValueError("description no puede exceder 500 caracteres")
