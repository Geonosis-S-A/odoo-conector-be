from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.users.application.use_cases.sync_users import SyncUsersUseCase
from app.users.application.use_cases.sync_single_user_changes import (
    SyncSingleUserChangesUseCase,
)
from app.users.application.use_cases.get_all_employees import GetAllEmployeesUseCase
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.api.schemas import (
    UserSyncResponse,
    SingleUserSyncResponse,
    EmployeesListResponse,
    EmployeeResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync", response_model=UserSyncResponse)
async def sync_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Sincroniza los usuarios desde Odoo a la base de datos local.
    - Los usuarios nuevos se crean como inactivos con sus roles de Odoo
    - Los usuarios existentes se actualizan con sus datos y roles más recientes
    - Mantiene el estado de activación e is_superuser de usuarios existentes
    """
    try:
        # Inicializar dependencias
        odoo_client = get_odoo_connection()
        employee_gateway = OdooEmployeeGateway(odoo_client)
        user_repository = SQLModelUserRepository(db)

        # Crear y ejecutar caso de uso
        use_case = SyncUsersUseCase(
            employee_gateway=employee_gateway,
            user_repository=user_repository,
        )

        # Ejecutar sincronización y obtener estadísticas
        sync_result = use_case.execute()

        return UserSyncResponse(
            success=True,
            message="Sincronización completada exitosamente",
            users_created=sync_result["created"],
            users_updated=sync_result["updated"],
            total_processed=sync_result["total_processed"],
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al sincronizar usuarios: {str(e)}"
        )


@router.post("/sync/{user_id}", response_model=SingleUserSyncResponse)
async def sync_user_changes(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Sincroniza cambios de un usuario específico desde Odoo.
    Actualiza email, nombre y roles del usuario identificado por ID.
    Mantiene el estado de activación e is_superuser del usuario.
    """

    roles: list[int] = current_user["roles"]
    is_admin = 30 in roles
    if not is_admin:
        raise HTTPException(
            status_code=403,
            detail="No tienes permisos para ver todos los usuarios",
        )
    try:
        # Inicializar dependencias
        odoo_client = get_odoo_connection()
        employee_gateway = OdooEmployeeGateway(odoo_client)
        user_repository = SQLModelUserRepository(db)

        # Crear y ejecutar caso de uso
        use_case = SyncSingleUserChangesUseCase(
            employee_gateway=employee_gateway,
            user_repository=user_repository,
        )

        # Ejecutar sincronización para el usuario específico
        result = use_case.execute(user_id)

        return SingleUserSyncResponse(
            success=result["success"],
            message=result["message"],
            user_updated=result["user_updated"],
            current_data=result.get("current_data"),
            changes_made=result.get("changes_made"),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al sincronizar usuario {user_id}: {str(e)}",
        )


@router.get("/employees", response_model=EmployeesListResponse)
async def get_all_employees(
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene todos los empleados registrados en Odoo.
    Retorna una lista completa de empleados con ID, email y nombre completo.
    """
    try:
        # Inicializar dependencias
        odoo_client = get_odoo_connection()
        employee_gateway = OdooEmployeeGateway(odoo_client)

        # Crear y ejecutar caso de uso
        use_case = GetAllEmployeesUseCase(employee_gateway=employee_gateway)

        # Ejecutar obtención de empleados
        employees = use_case.execute()

        # Convertir Employee del dominio a EmployeeResponse del schema
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

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al obtener empleados: {str(e)}"
        )
