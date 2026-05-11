"""
Helpers de autorización a nivel de scope/recurso.

Estos helpers complementan la autorización por rol (`user_has_role`) agregando
una capa de "ownership" o "team membership": además de tener el rol correcto,
el usuario debe tener relación con el recurso que está intentando consultar
o modificar.

Surgieron a partir del pentest 2026-04 (VT-02), donde se identificaron varios
IDORs / Broken Object-Level Authorization en endpoints que solo verificaban el
rol del usuario pero no validaban que el `employee_id` recibido por path o
body perteneciera al equipo del solicitante.

OWASP: A01:2021 Broken Access Control / CWE-639 Authorization Bypass Through
User-Controlled Key.
"""

from fastapi import HTTPException, status

from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway


def ensure_employee_in_team(
    *,
    requester_user_id: int,
    target_employee_id: int,
    employee_gateway: EmployeeGateway,
    timesheet_gateway: TimesheetLineGateway,
) -> None:
    """
    Valida que `target_employee_id` esté dentro del scope de equipo del usuario
    solicitante, usando la jerarquía de Odoo.

    El scope se considera válido si:
      - El `target_employee_id` coincide con el propio empleado del solicitante
        (self-access, p. ej. un manager consultando su propio costo).
      - O el `target_employee_id` aparece en la lista que devuelve
        `TimesheetLineGateway.get_team_users` para el solicitante (subordinados
        directos + cadena descendente según `child_of` en Odoo).

    En cualquier otro caso lanza HTTP 403.

    Args:
        requester_user_id: ID de usuario (app) del solicitante autenticado.
        target_employee_id: ID de empleado (Odoo) del recurso al que se quiere
            acceder.
        employee_gateway: Gateway para resolver el empleado del solicitante.
        timesheet_gateway: Gateway que expone la jerarquía de Odoo.

    Raises:
        HTTPException: 403 si el solicitante no tiene empleado asociado o si el
            `target_employee_id` no está en su equipo.

    Nota de seguridad:
        Por diseño, ante un `target_employee_id` que no está en el equipo se
        responde 403 sin distinguir si el empleado existe o no. Esto evita que
        un atacante use respuestas distintas (403 vs 404) para enumerar IDs
        válidos en el sistema.
    """
    requester_employee = employee_gateway.get_by_id(requester_user_id)
    if requester_employee is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un empleado asociado en Odoo",
        )

    if target_employee_id == requester_employee.id:
        return

    team_users = timesheet_gateway.get_team_users(
        requester_user_id, requester_employee.id
    )
    team_ids = {member["id"] for member in team_users}

    if target_employee_id not in team_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para operar sobre este empleado",
        )
