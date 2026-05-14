from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.infra.auth_service import JWTPayload
from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import is_privileged_user
from app.users.application.use_cases.sync_single_user_changes import (
    SyncSingleUserChangesUseCase,
)
from app.users.application.use_cases.get_all_employees import GetAllEmployeesUseCase
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.api.schemas import (
    SingleUserSyncResponse,
    EmployeesListResponse,
    EmployeesListPublicResponse,
    EmployeeResponse,
    EmployeePublicResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync/{employee_id}", response_model=SingleUserSyncResponse)
async def sync_user_changes(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Sincroniza cambios de un empleado específico desde Odoo.
    Recibe el ID del empleado y verifica si tiene un usuario asociado.
    Si tiene usuario asociado: actualiza email, nombre y roles del usuario.
    Si no tiene usuario asociado: retorna mensaje informativo.
    Mantiene el estado de activación e is_superuser del usuario.

    Seguridad: el campo `roles` dentro de `changes_made` solo se incluye
    si el solicitante tiene rol approver O está sincronizando su propia cuenta.
    """
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)
    user_repository = SQLModelUserRepository(db)

    use_case = SyncSingleUserChangesUseCase(
        employee_gateway=employee_gateway,
        user_repository=user_repository,
    )

    result = use_case.execute(employee_id)

    # Ocultar info de roles en changes_made para usuarios sin privilegios
    # que no están sincronizando su propia cuenta (OWASP A07).
    changes_made = result.get("changes_made")
    requester_is_privileged = is_privileged_user(current_user.get("roles"))
    requester_is_self = current_user.get("user_id") == employee_id

    if changes_made and not requester_is_privileged and not requester_is_self:
        changes_made = {k: v for k, v in changes_made.items() if k != "roles"}

    return SingleUserSyncResponse(
        success=result["success"],
        message=result["message"],
        user_updated=result["user_updated"],
        current_data=result.get("current_data"),
        changes_made=changes_made,
    )


@router.get("/employees")
async def get_all_employees(
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Obtiene empleados registrados en Odoo.

    - Approvers: lista completa con ID, email y nombre.
    - Resto de usuarios autenticados: solo nombre completo (para autocomplete),
      sin email ni ID interno, para prevenir enumeración de cuentas (OWASP A07).
    """
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)

    use_case = GetAllEmployeesUseCase(employee_gateway=employee_gateway)
    employees = use_case.execute()

    if is_privileged_user(current_user.get("roles")):
        employees_response = [
            EmployeeResponse(
                id=employee.id,
                email=employee.email,
                full_name=employee.full_name,
            )
            for employee in employees
        ]
        return EmployeesListResponse(
            success=True,
            message="Empleados obtenidos exitosamente",
            employees=employees_response,
            total_employees=len(employees_response),
        )

    # Respuesta reducida: solo nombre, sin email ni ID
    employees_public = [
        EmployeePublicResponse(full_name=employee.full_name)
        for employee in employees
    ]
    return EmployeesListPublicResponse(
        success=True,
        message="Empleados obtenidos exitosamente",
        employees=employees_public,
        total_employees=len(employees_public),
    )

