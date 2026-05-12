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

from dataclasses import dataclass

from fastapi import HTTPException, status

from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.users.domain.repositories import EmployeeGateway


@dataclass(frozen=True)
class TeamScope:
    """Snapshot del scope de un solicitante: su propio employee_id en Odoo y
    el conjunto de IDs de empleados que están bajo su jerarquía.

    Se calcula una sola vez por request con `get_team_scope(...)` y se consulta
    con `contains(...)`. Esto evita hacer N llamadas a Odoo cuando un mismo
    endpoint necesita validar la pertenencia de varios `employee_id`
    (p. ej. `DELETE /timesheet/` con N IDs en el body).
    """

    requester_employee_id: int
    team_member_ids: frozenset[int]

    def contains(self, target_employee_id: int) -> bool:
        """True si el target es el propio solicitante o pertenece a su equipo."""
        return (
            target_employee_id == self.requester_employee_id
            or target_employee_id in self.team_member_ids
        )


def get_team_scope(
    *,
    requester_user_id: int,
    employee_gateway: EmployeeGateway,
    timesheet_gateway: TimesheetLineGateway,
) -> TeamScope:
    """Resuelve el scope de equipo del solicitante consultando Odoo.

    Realiza dos llamadas a Odoo:
      1) `employee_gateway.get_by_id(requester_user_id)` para obtener el
         `Employee` asociado.
      2) `timesheet_gateway.get_team_users(...)` para obtener la jerarquía
         descendente (subordinados directos + cadena `child_of`).

    Raises:
        HTTPException 403: si el solicitante no tiene `Employee` asociado en
            Odoo. Sin ese vínculo no se puede determinar scope, así que se
            deniega por defecto (fail-closed).
    """
    requester_employee = employee_gateway.get_by_id(requester_user_id)
    if requester_employee is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un empleado asociado en Odoo",
        )

    team_users = timesheet_gateway.get_team_users(
        requester_user_id, requester_employee.id
    )
    team_member_ids = frozenset(member["id"] for member in team_users)

    return TeamScope(
        requester_employee_id=requester_employee.id,
        team_member_ids=team_member_ids,
    )


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
    scope = get_team_scope(
        requester_user_id=requester_user_id,
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )

    if not scope.contains(target_employee_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para operar sobre este empleado",
        )


def ensure_owns_timesheets(
    *,
    requester_user_id: int,
    target_employee_ids: list[int],
    employee_gateway: EmployeeGateway,
    timesheet_gateway: TimesheetLineGateway,
) -> None:
    """
    Variante de `ensure_employee_in_team` para una colección de targets.

    Resuelve el `TeamScope` UNA SOLA vez y luego itera localmente, evitando
    N+1 llamadas a Odoo cuando el caller necesita validar la pertenencia de
    varios `employee_id` en la misma request (p. ej. borrar / validar varios
    timesheets en lote).

    Pensada para los IDOR/BFLA reportados en VT-04 (PUT/DELETE timesheet) y
    VT-14 (POST /timesheet/validate) del pentest 2026-04.

    Raises:
        HTTPException: 403 si cualquiera de los `target_employee_ids` cae
            fuera del scope del solicitante. Se aborta a la primera falla
            (semántica "todo o nada", para que la operación quede atómica).
    """
    scope = get_team_scope(
        requester_user_id=requester_user_id,
        employee_gateway=employee_gateway,
        timesheet_gateway=timesheet_gateway,
    )

    for target_employee_id in target_employee_ids:
        if not scope.contains(target_employee_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para operar sobre uno o más de estos recursos",
            )
