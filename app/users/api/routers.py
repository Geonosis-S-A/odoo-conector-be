from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.users.application.use_cases.sync_users import SyncUsersUseCase
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.api.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync", response_model=List[UserResponse])
async def sync_users(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Sincroniza los usuarios desde Odoo a la base de datos local.
    Los usuarios nuevos se crean como inactivos.
    Los usuarios existentes mantienen su estado pero se actualizan sus datos.
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
        use_case.execute()

        # Obtener y devolver usuarios actualizados
        updated_users = user_repository.all()
        return updated_users

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al sincronizar usuarios: {str(e)}"
        )
