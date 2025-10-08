from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.infra.auth_service import JWTPayload
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.employee_price.application.use_cases.sync_users_to_employee_price import (
    SyncUsersToEmployeePriceUseCase,
)
from app.employee_price.application.use_cases.set_active_employee_cost_per_hour import (
    SetEmployeeCostPerHourUseCase,
)
from app.employee_price.infra.db.repositories import SQLModelEmployeePriceRepository
from app.users.infra.db.repositories import SQLModelUserRepository
from app.employee_price.api.schemas import (
    SyncUsersToEmployeePriceResponse,
    SetCostPerHourRequest,
    SetCostPerHourResponse,
)
from app.employee_price.api.schemas import EmployeePriceResponse, SetCostPerHourRequest, SetCostPerHourResponse

router = APIRouter(prefix="/employee-price", tags=["employee-price"])


@router.post("/sync", response_model=SyncUsersToEmployeePriceResponse)
async def sync_users_to_employee_price(
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Sincroniza todos los usuarios a la tabla employee_price.
    
    Crea un registro de precio para cada usuario existente con:
    - date_from = fecha actual
    - date_to = fecha actual
    - cost_per_hour = None (se debe configurar posteriormente)
    
    Omite usuarios que ya tienen un registro activo en la fecha actual.
    """

    try:
        # Inicializar repositorios
        user_repository = SQLModelUserRepository(db)
        employee_price_repository = SQLModelEmployeePriceRepository(db)

        # Crear y ejecutar caso de uso
        use_case = SyncUsersToEmployeePriceUseCase(
            user_repository=user_repository,
            employee_price_repository=employee_price_repository,
        )

        # Ejecutar sincronización
        result = use_case.execute()

        return SyncUsersToEmployeePriceResponse(
            success=result["success"],
            message=result["message"],
            total_users=result["total_users"],
            synced_count=result["synced_count"],
            skipped_count=result["skipped_count"],
            failed_count=result["failed_count"],
            details=result.get("details"),
        )

    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise


@router.patch("/{user_id}", response_model=SetCostPerHourResponse)
async def set_active_employee_cost_per_hour(
    user_id: int,
    request: SetCostPerHourRequest,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Actualiza el costo por hora del registro activo de un usuario.
    
    Busca el registro de employee_price activo en la fecha actual
    y actualiza su costo por hora.
    
    Args:
        user_id: ID del usuario
        request: Datos con el nuevo costo por hora
    
    Returns:
        SetCostPerHourResponse con el registro actualizado
        
    Raises:
        HTTPException 404: Si no se encuentra un registro activo para el usuario
        HTTPException 400: Si el costo por hora es inválido
        HTTPException 500: Si hay un error al procesar la actualización
    """

    # Inicializar repositorio
    employee_price_repository = SQLModelEmployeePriceRepository(db)

    # Crear y ejecutar caso de uso
    use_case = SetEmployeeCostPerHourUseCase(
        employee_price_repository=employee_price_repository
    )

    try:
        # Ejecutar actualización
        updated_price = use_case.execute(user_id, request.cost_per_hour)

        # Si no se encuentra el registro activo
        if not updated_price or updated_price.id is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró un registro activo para el usuario con ID {user_id}",
            )

        # Convertir a response schema
        employee_price_response = EmployeePriceResponse(
            id=updated_price.id,
            user_id=updated_price.user_id,
            email=updated_price.email,
            full_name=updated_price.full_name,
            date_from=updated_price.date_from,
            cost_per_hour=updated_price.cost_per_hour,
            date_to=updated_price.date_to,
        )
        
        return SetCostPerHourResponse(
            success=True,
            message="Costo por hora actualizado exitosamente",
            employee_price=employee_price_response,
        )

    except ValueError as e:
        # Errores de validación de negocio (ej: cost_per_hour <= 0)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise

