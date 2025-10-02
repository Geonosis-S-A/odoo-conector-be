from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.infra.auth_service import JWTPayload
from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.users.application.use_cases.sync_single_user_changes import (
    SyncSingleUserChangesUseCase,
)
from app.users.application.use_cases.get_all_employees import GetAllEmployeesUseCase
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
):
    """
    Obtiene todos los empleados registrados en Odoo.
    Retorna una lista completa de empleados con ID, email y nombre completo.
    """

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

        
