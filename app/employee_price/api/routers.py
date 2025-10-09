from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.auth.infra.auth_service import JWTPayload
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.employee_price.infra.db.repositories import SQLModelEmployeePriceRepository
from app.users.infra.db.repositories import SQLModelUserRepository
from app.employee_price.api.schemas import (
    CreateEmployeePriceRequest,
    CreateEmployeePriceResponse,
    EmployeePriceWithUserResponse,
)
from app.employee_price.application.use_cases.create_employee_price import (
    CreateEmployeePriceUseCase,
)

router = APIRouter(prefix="/employee-price", tags=["employee-price"])


@router.post("/", response_model=CreateEmployeePriceResponse)
async def create_employee_price(
    request: CreateEmployeePriceRequest,
    db: Session = Depends(get_db),
    current_user: JWTPayload = Depends(get_current_user),
):
    """
    Crea un nuevo registro de precio por hora para un empleado.
    
    Si existe un registro activo previo (con date_to vacío), automáticamente
    se cerrará ese registro estableciendo su date_to.
    
    Args:
        request: Datos del nuevo registro de precio de empleado
        db: Sesión de base de datos
        current_user: Usuario autenticado
    
    Returns:
        CreateEmployeePriceResponse con el registro creado
        
    Raises:
        HTTPException 400: Si los datos son inválidos (costo <= 0, fechas incorrectas, etc.)
        HTTPException 404: Si el usuario no existe
    """
    # Inicializar repositorios
    employee_price_repository = SQLModelEmployeePriceRepository(db)
    user_repository = SQLModelUserRepository(db)

    # Verificar que el usuario existe
    user = user_repository.get_by_id(request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuario con ID {request.user_id} no encontrado",
        )

    # Crear y ejecutar caso de uso
    use_case = CreateEmployeePriceUseCase(
        employee_price_repository=employee_price_repository
    )

    try:
        # Ejecutar creación
        created_employee_price = use_case.execute(
            user_id=request.user_id,
            date_from=request.date_from,
            cost_per_hour=request.cost_per_hour,
        )

        # Validar que el registro fue creado correctamente
        if created_employee_price.id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Error al crear el registro de precio de empleado",
            )

        # Convertir a response schema con datos del usuario
        employee_price_response = EmployeePriceWithUserResponse(
            id=created_employee_price.id,
            user_id=created_employee_price.user_id,
            email=user.email,
            full_name=user.full_name,
            date_from=created_employee_price.date_from,
            cost_per_hour=created_employee_price.cost_per_hour,
            date_to=created_employee_price.date_to,
        )

        return CreateEmployeePriceResponse(
            success=True,
            message="Registro de precio de empleado creado exitosamente",
            employee_price=employee_price_response,
        )

    except ValueError as e:
        # Errores de validación de negocio
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except HTTPException:
        # Re-lanzar HTTPExceptions tal como están
        raise



