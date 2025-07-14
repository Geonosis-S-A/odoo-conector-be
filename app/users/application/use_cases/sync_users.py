from app.users.domain.repositories import EmployeeGateway, UserRepository
from app.users.domain.models import User


class SyncUsersUseCase:
    def __init__(
        self, employee_gateway: EmployeeGateway, user_repository: UserRepository
    ):
        self.gateway = employee_gateway
        self.repo = user_repository

    def execute(self):
        # 1. Obtener empleados de Odoo
        odoo_employees = self.gateway.all()

        # 2. Obtener usuarios actuales de la base de datos
        current_users = self.repo.all()

        # 3. Crear lista de usuarios a sincronizar
        users_to_sync = []
        for employee in odoo_employees:
            # Buscar si el empleado ya existe en nuestra base de datos por ID
            existing_user = next(
                (user for user in current_users if user.id == employee.id), None
            )

            if not existing_user:
                # Si no existe, creamos uno nuevo inactivo
                user = User(
                    id=employee.id,
                    email=employee.email,
                    full_name=employee.full_name,
                    is_active=False,
                    is_superuser=False,
                )
                users_to_sync.append(user)

        # 4. Guardar todos los usuarios en la base de datos
        if users_to_sync:  # Solo guardamos si hay usuarios nuevos
            self.repo.save_all(users_to_sync)
