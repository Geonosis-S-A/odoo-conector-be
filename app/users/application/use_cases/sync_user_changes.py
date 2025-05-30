from app.users.domain.repositories import EmployeeGateway, UserRepository
from app.users.domain.models import User
from typing import List, Dict


class SyncUserChangesUseCase:
    def __init__(
        self, employee_gateway: EmployeeGateway, user_repository: UserRepository
    ):
        self.employee_gateway = employee_gateway
        self.user_repository = user_repository

    def execute(self) -> Dict[str, List[User]]:
        """
        Sincroniza cambios de empleados desde Odoo SOLO para usuarios existentes.
        No crea usuarios nuevos - eso se maneja por el login.

        Returns:
            Dict con listas de usuarios actualizados y sin cambios
        """
        # 1. Obtener empleados de Odoo
        odoo_employees = self.employee_gateway.all()

        # 2. Obtener usuarios actuales de la base de datos
        current_users = self.user_repository.all()
        current_users_dict = {user.id: user for user in current_users if user.id}

        # 3. Crear mapa de empleados de Odoo para búsqueda rápida
        odoo_employees_dict = {emp.id: emp for emp in odoo_employees}

        # 4. Solo procesar usuarios que existen en ambos lados
        users_updated = []
        users_unchanged = []

        for user_id, current_user in current_users_dict.items():
            odoo_employee = odoo_employees_dict.get(user_id)

            if not odoo_employee:
                # Usuario existe en BD pero no en Odoo - mantener sin cambios
                users_unchanged.append(current_user)
                continue

            # Verificar si hay cambios
            if (
                current_user.email != odoo_employee.email
                or current_user.full_name != odoo_employee.full_name
            ):
                # Crear usuario actualizado manteniendo estado actual
                updated_user = User(
                    id=current_user.id,
                    email=odoo_employee.email,
                    full_name=odoo_employee.full_name,
                    is_active=current_user.is_active,
                    is_superuser=current_user.is_superuser,
                )
                self.user_repository.update_user(updated_user)
                users_updated.append(updated_user)
            else:
                # Sin cambios
                users_unchanged.append(current_user)

        return {
            "updated": users_updated,
            "unchanged": users_unchanged,
        }
