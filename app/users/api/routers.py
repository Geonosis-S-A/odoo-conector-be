from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.infra.auth_service import JWTPayload
from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.team.api.dependencies import get_team_access_service
from app.team.application.team_access import TeamAccessService
from app.users.application.use_cases.sync_single_user_changes import (
    SyncSingleUserChangesUseCase,
)
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.api.schemas import (
    SingleUserSyncResponse,
    EmployeesListResponse,
    EmployeeResponse,
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
    """

    
    # Inicializar dependencias
    odoo_client = get_odoo_connection()
    employee_gateway = OdooEmployeeGateway(odoo_client)
    user_repository = SQLModelUserRepository(db)

    # Crear y ejecutar caso de uso
    use_case = SyncSingleUserChangesUseCase(
        employee_gateway=employee_gateway,
        user_repository=user_repository,
    )

    # Ejecutar sincronización para el empleado específico
    result = use_case.execute(employee_id)

    return SingleUserSyncResponse(
        success=result["success"],
        message=result["message"],
        user_updated=result["user_updated"],
        current_data=result.get("current_data"),
        changes_made=result.get("changes_made"),
    )

    


@router.get("/employees", response_model=EmployeesListResponse)
async def get_all_employees(
    current_user: JWTPayload = Depends(get_current_user),
    team_access: TeamAccessService = Depends(get_team_access_service),
):
    """
    Obtiene los empleados visibles para el usuario autenticado: su equipo
    (jerarquía Odoo ∪ proyectos que gerencia) más los equipos ajenos donde
    tenga un permiso de vista/validación delegado.
    """

    members = team_access.visible_team_members(current_user["user_id"])

    # Convertir TeamMemberInfo a EmployeeResponse del schema
    employees_response = [
        EmployeeResponse(
            id=member.employee_odoo_id,
            email=member.email or "",
            full_name=member.name or "",
        )
        for member in members
    ]

    return EmployeesListResponse(
        success=True,
        message="Empleados obtenidos exitosamente",
        employees=employees_response,
        total_employees=len(employees_response),
    )

        
