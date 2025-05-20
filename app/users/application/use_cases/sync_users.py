from app.users.domain.repositories import EmployeeGateway, UserRepository


class SyncUsersUseCase:
    def __init__(
        self, employee_gateway: EmployeeGateway, user_repository: UserRepository
    ):
        self.gateway = employee_gateway
        self.repo = user_repository

    def execute(self):
        # 1. Tomar usuarios del repo y del odoo
        # 2. Los que no estén en el bbdd hay que cargarlos como not active y sin password o uno random
        pass
