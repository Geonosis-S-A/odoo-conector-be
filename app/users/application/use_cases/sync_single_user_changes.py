from app.users.domain.repositories import EmployeeGateway, UserRepository
from app.users.domain.models import User
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from typing import Optional, Dict, Any


class SyncSingleUserChangesUseCase:
    def __init__(
        self, employee_gateway: EmployeeGateway, user_repository: UserRepository
    ):
        self.employee_gateway = employee_gateway
        self.user_repository = user_repository

    def execute(self, user_id: int) -> Dict[str, Any]:
        """
        Sincroniza cambios de un usuario específico desde Odoo.
        Actualiza email, nombre y roles si han cambiado.

        Args:
            user_email: Email del usuario a sincronizar

        Returns:
            Dict con información del resultado de la sincronización
        """
        # Verificar que el gateway sea OdooEmployeeGateway para acceder a métodos específicos
        if not isinstance(self.employee_gateway, OdooEmployeeGateway):
            raise ValueError(
                "Gateway debe ser OdooEmployeeGateway para sincronización con roles"
            )

        # 1. Buscar el usuario en la base de datos local
        local_user = self.user_repository.get_by_id(user_id)
        if not local_user:
            return {
                "success": False,
                "message": f"Usuario con id {user_id} no encontrado en la base de datos local",
                "user_updated": False,
            }

        # 2. Obtener datos del usuario desde Odoo (incluyendo roles)
        odoo_users = self.employee_gateway.get_all_users_with_roles()
        odoo_user = next(
            (user for user in odoo_users if user.get("id") == user_id), None
        )

        if not odoo_user:
            return {
                "success": False,
                "message": f"Usuario con id {user_id} no encontrado en Odoo",
                "user_updated": False,
            }

        # 3. Comparar y verificar si hay cambios
        odoo_name = odoo_user.get("name", "")
        odoo_email = odoo_user.get("email", "")
        odoo_roles = odoo_user.get("roles", [])

        has_changes = (
            local_user.email != odoo_email
            or local_user.full_name != odoo_name
            or local_user.roles != odoo_roles
        )

        if not has_changes:
            return {
                "success": True,
                "message": "No hay cambios que sincronizar",
                "user_updated": False,
                "current_data": {
                    "email": local_user.email,
                    "full_name": local_user.full_name,
                    "roles": local_user.roles,
                    "is_active": local_user.is_active,
                },
            }

        # 4. Actualizar usuario con datos de Odoo
        updated_user = User(
            id=local_user.id,
            email=odoo_email,
            full_name=odoo_name,
            is_active=local_user.is_active,  # Mantener estado actual
            is_superuser=local_user.is_superuser,  # Mantener estado actual
            roles=odoo_roles,
        )

        # 5. Guardar cambios
        success = self.user_repository.update_user(updated_user)

        if success:
            return {
                "success": True,
                "message": "Usuario sincronizado exitosamente",
                "user_updated": True,
                "changes_made": {
                    "email": {
                        "old": local_user.email,
                        "new": odoo_email,
                        "changed": local_user.email != odoo_email,
                    },
                    "full_name": {
                        "old": local_user.full_name,
                        "new": odoo_name,
                        "changed": local_user.full_name != odoo_name,
                    },
                    "roles": {
                        "old": local_user.roles,
                        "new": odoo_roles,
                        "changed": local_user.roles != odoo_roles,
                    },
                },
            }
        else:
            return {
                "success": False,
                "message": f"Error al actualizar usuario {user_id} en la base de datos",
                "user_updated": False,
            }
