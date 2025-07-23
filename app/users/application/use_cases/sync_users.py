from app.users.domain.repositories import EmployeeGateway, UserRepository
from app.users.domain.models import User
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from typing import List


class SyncUsersUseCase:
    def __init__(
        self, employee_gateway: EmployeeGateway, user_repository: UserRepository
    ):
        self.gateway = employee_gateway
        self.repo = user_repository

    def execute(self):
        """
        Sincroniza usuarios desde Odoo incluyendo sus roles.
        - Crea usuarios nuevos como inactivos con sus roles
        - Actualiza roles de usuarios existentes
        """
        # Verificar que el gateway sea OdooEmployeeGateway para acceder al método específico
        if not isinstance(self.gateway, OdooEmployeeGateway):
            raise ValueError(
                "Gateway debe ser OdooEmployeeGateway para sincronización con roles"
            )

        # 1. Obtener usuarios con roles desde Odoo
        odoo_users_with_roles = self.gateway.get_all_users_with_roles()

        # 2. Obtener usuarios actuales de la base de datos
        current_users = self.repo.all()

        # 3. Procesar sincronización
        new_users = []
        updated_users = []

        for odoo_user in odoo_users_with_roles:
            user_id = odoo_user.get("id")
            user_name = odoo_user.get("name", "")
            user_email = odoo_user.get("email", "")
            user_roles = odoo_user.get("roles", [])

            # Buscar si el usuario ya existe en nuestra base de datos por ID
            existing_user = next(
                (user for user in current_users if user.id == user_id), None
            )

            if existing_user:
                # Usuario existente: actualizar datos y roles si han cambiado
                needs_update = (
                    existing_user.email != user_email
                    or existing_user.full_name != user_name
                    or existing_user.roles != user_roles
                )

                if needs_update:
                    updated_user = User(
                        id=user_id,
                        email=user_email,
                        full_name=user_name,
                        is_active=existing_user.is_active,  # Mantener estado actual
                        is_superuser=existing_user.is_superuser,  # Mantener estado actual
                        roles=user_roles,
                    )
                    updated_users.append(updated_user)
            else:
                # Usuario nuevo: crear como inactivo con roles
                new_user = User(
                    id=user_id,
                    email=user_email,
                    full_name=user_name,
                    is_active=False,  # Inactivo por defecto
                    is_superuser=False,  # No superusuario por defecto
                    roles=user_roles,
                )
                new_users.append(new_user)

        # 4. Guardar cambios en la base de datos
        created_count = 0
        updated_count = 0

        # Guardar usuarios nuevos
        if new_users:
            self.repo.save_all(new_users)
            created_count = len(new_users)

        # Actualizar usuarios existentes
        for user in updated_users:
            if self.repo.update_user(user):
                updated_count += 1

        print(f"✅ Sincronización completada:")
        print(f"   📝 {created_count} usuarios creados")
        print(f"   🔄 {updated_count} usuarios actualizados")
        print(f"   👥 {len(odoo_users_with_roles)} usuarios procesados desde Odoo")

        return {
            "created": created_count,
            "updated": updated_count,
            "total_processed": len(odoo_users_with_roles),
        }
