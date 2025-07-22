from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.shared.infra.db.session import get_db
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.users.application.use_cases.sync_users import SyncUsersUseCase
from app.users.application.use_cases.sync_user_changes import SyncUserChangesUseCase
from app.users.infra.db.repositories import SQLModelUserRepository
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.users.api.schemas import UserResponse, UserSyncResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/sync", response_model=UserSyncResponse)
async def sync_users(
    db: Session = Depends(get_db),
    # current_user: dict = Depends(get_current_user),
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


# @router.post("/sync-changes", response_model=UserSyncResponse)
# async def sync_user_changes(
#     db: Session = Depends(get_db),
#     # current_user: dict = Depends(get_current_user),
# ):
#     """
#     Sincroniza cambios de empleados desde Odoo SOLO para usuarios existentes.
#     NO crea usuarios nuevos - eso se maneja por el proceso de login.
#     Solo actualiza los campos email y full_name, manteniendo el estado actual del usuario.
#     """
#     try:
#         # Inicializar dependencias
#         odoo_client = get_odoo_connection()
#         employee_gateway = OdooEmployeeGateway(odoo_client)
#         user_repository = SQLModelUserRepository(db)

#         # Crear y ejecutar caso de uso
#         use_case = SyncUserChangesUseCase(
#             employee_gateway=employee_gateway,
#             user_repository=user_repository,
#         )
#         result = use_case.execute()

#         # Crear resumen
#         summary = (
#             f"Actualizados: {len(result['updated'])}, "
#             f"Sin cambios: {len(result['unchanged'])}"
#         )

#         return UserSyncResponse(
#             updated=[
#                 UserResponse(
#                     id=user.id,
#                     email=user.email,
#                     full_name=user.full_name,
#                     is_active=user.is_active,
#                     is_superuser=user.is_superuser,
#                 )
#                 for user in result["updated"]
#                 if user.id is not None
#             ],
#             unchanged=[
#                 UserResponse(
#                     id=user.id,
#                     email=user.email,
#                     full_name=user.full_name,
#                     is_active=user.is_active,
#                     is_superuser=user.is_superuser,
#                 )
#                 for user in result["unchanged"]
#                 if user.id is not None
#             ],
#             summary=summary,
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error al sincronizar cambios de usuarios: {str(e)}",
#         )
