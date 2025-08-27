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

    def execute(self, employee_id: int) -> Dict[str, Any]:
        """
        Sincroniza cambios de un empleado específico desde Odoo.
        Actualiza email, nombre y roles (si el empleado tiene user_id asociado) si han cambiado.

        Args:
            employee_id: ID del empleado a sincronizar

        Returns:
            Dict con información del resultado de la sincronización
        """
        # Verificar que el gateway sea OdooEmployeeGateway para acceder a métodos específicos
        if not isinstance(self.employee_gateway, OdooEmployeeGateway):
            raise ValueError(
                "Gateway debe ser OdooEmployeeGateway para sincronización con roles"
            )

        # 1. Obtener datos del empleado desde Odoo (incluyendo si tiene usuario asociado)
        odoo_employee_data = self.employee_gateway.get_employee_with_user_data(
            employee_id
        )
        if not odoo_employee_data:
            return {
                "success": False,
                "message": f"Empleado con id {employee_id} no encontrado en Odoo",
                "user_updated": False,
            }

        # 2. Verificar si el empleado tiene un usuario asociado
        has_user = odoo_employee_data.get("has_user", False)
        user_id = odoo_employee_data.get("user_id")
        odoo_name = odoo_employee_data.get("name", "")
        odoo_email = odoo_employee_data.get("email", "")
        odoo_roles = odoo_employee_data.get("roles", [])

        # 3. Buscar el usuario en la base de datos local
        if has_user and user_id:
            # Empleado CON user_id: buscar por ID y sincronizar nombre, email y roles
            local_employee = self.user_repository.get_by_id(employee_id)
            if not local_employee:
                return {
                    "success": False,
                    "message": f"Usuario con id {user_id} (asociado al empleado {employee_id}) no encontrado en la base de datos local",
                    "user_updated": False,
                }

            # Comparar cambios incluyendo roles
            has_changes = (
                local_employee.email != odoo_email
                or local_employee.full_name != odoo_name
                or set(local_employee.roles or []) != set(odoo_roles or [])
            )

            changes_detail = {
                "employee_id": employee_id,
                "user_id": user_id,
                "has_user_id": True,
                "email": {
                    "old": local_employee.email,
                    "new": odoo_email,
                    "changed": local_employee.email != odoo_email,
                },
                "full_name": {
                    "old": local_employee.full_name,
                    "new": odoo_name,
                    "changed": local_employee.full_name != odoo_name,
                },
                "roles": {
                    "old": local_employee.roles,
                    "new": odoo_roles,
                    "changed": local_employee.roles != odoo_roles,
                },
            }

        else:
            # Empleado SIN user_id: buscar por email y sincronizar solo nombre y email
            local_employee = self.user_repository.get_by_email(odoo_email)
            if not local_employee:
                return {
                    "success": False,
                    "message": f"Usuario con email {odoo_email} (empleado {employee_id}) no encontrado en la base de datos local",
                    "user_updated": False,
                }

            # Comparar cambios SIN incluir roles
            has_changes = (
                local_employee.email != odoo_email
                or local_employee.full_name != odoo_name
            )

            # Mantener los roles actuales del usuario local
            odoo_roles = local_employee.roles

            changes_detail = {
                "employee_id": employee_id,
                "user_id": local_employee.id,
                "has_user_id": False,
                "email": {
                    "old": local_employee.email,
                    "new": odoo_email,
                    "changed": local_employee.email != odoo_email,
                },
                "full_name": {
                    "old": local_employee.full_name,
                    "new": odoo_name,
                    "changed": local_employee.full_name != odoo_name,
                },
                "roles": {
                    "old": local_employee.roles,
                    "new": local_employee.roles,  # Sin cambios en roles
                    "changed": False,
                },
            }

        # 4. Verificar si hay cambios que aplicar
        if not has_changes:
            return {
                "success": True,
                "message": "No hay cambios que sincronizar",
                "user_updated": False,
                "current_data": {
                    "employee_id": employee_id,
                    "user_id": None,
                    "has_user_id": has_user,
                    "email": local_employee.email,
                    "full_name": local_employee.full_name,
                    "roles": local_employee.roles,
                    "is_active": local_employee.is_active,
                },
            }

        # 5. Actualizar usuario con datos de Odoo
        updated_user = User(
            id=local_employee.id,
            email=odoo_email,
            full_name=odoo_name,
            is_active=local_employee.is_active,  # Mantener estado actual
            is_superuser=local_employee.is_superuser,  # Mantener estado actual
            roles=odoo_roles,  # Usar roles de Odoo solo si tiene user_id, sino mantener actuales
        )

        # 6. Guardar cambios
        success = self.user_repository.update_user(updated_user)

        if success:
            return {
                "success": True,
                "message": f"Usuario sincronizado exitosamente ({'con roles' if has_user else 'solo nombre/email'})",
                "user_updated": True,
                "changes_made": changes_detail,
            }
        else:
            return {
                "success": False,
                "message": f"Error al actualizar usuario {local_employee.id} (empleado {employee_id}) en la base de datos",
                "user_updated": False,
            }
