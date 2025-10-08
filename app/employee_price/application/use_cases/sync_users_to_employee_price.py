from datetime import date
from typing import Dict, Any, List
from app.employee_price.domain.models import EmployeePrice
from app.employee_price.domain.repositories import EmployeePriceRepository
from app.users.domain.repositories import UserRepository


class SyncUsersToEmployeePriceUseCase:
    """
    Caso de uso para sincronizar usuarios a la tabla de precios de empleados.
    Crea registros en employee_price para todos los usuarios existentes.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        employee_price_repository: EmployeePriceRepository,
    ):
        self.user_repository = user_repository
        self.employee_price_repository = employee_price_repository

    def execute(self) -> Dict[str, Any]:
        """
        Ejecuta la sincronización de usuarios a employee_price.

        Para cada usuario en UserModel crea un registro en EmployeePrice con:
        - date_from = hoy
        - date_to = hoy
        - cost_per_hour = None (opcional)

        Returns:
            Dict con información del resultado de la sincronización
        """
        # 1. Obtener todos los usuarios
        all_users = self.user_repository.all()

        if not all_users:
            return {
                "success": True,
                "message": "No hay usuarios para sincronizar",
                "total_users": 0,
                "synced_count": 0,
                "skipped_count": 0,
                "failed_count": 0,
                "details": [],
            }

        # 2. Fecha de hoy para date_from y date_to
        today = date.today()

        synced_employees: List[EmployeePrice] = []
        skipped_users: List[Dict[str, Any]] = []
        failed_users: List[Dict[str, Any]] = []

        # 3. Para cada usuario, crear registro de precio
        for user in all_users:
            try:
                # Validar que el usuario tenga ID
                if user.id is None:
                    failed_users.append(
                        {
                            "user_id": 0,
                            "email": user.email,
                            "error": "Usuario sin ID",
                        }
                    )
                    continue

                # Verificar si ya existe un registro activo para este usuario
                existing_price = self.employee_price_repository.get_active_by_user_id(
                    user.id, today
                )

                if existing_price:
                    skipped_users.append(
                        {
                            "user_id": user.id,
                            "email": user.email,
                            "reason": "Ya existe un registro activo para este usuario",
                        }
                    )
                    continue

                # Crear nuevo registro de precio
                employee_price = EmployeePrice(
                    id=None,
                    user_id=user.id,
                    email=user.email,
                    full_name=user.full_name,
                    date_from=today,
                    cost_per_hour=None,  # Opcional, se debe configurar posteriormente
                    date_to=today,
                )

                # Guardar en la base de datos
                saved_price = self.employee_price_repository.save(employee_price)
                synced_employees.append(saved_price)

            except Exception as e:
                failed_users.append(
                    {
                        "user_id": user.id,
                        "email": user.email,
                        "error": str(e),
                    }
                )

        # 4. Preparar respuesta detallada
        return {
            "success": True,
            "message": f"Sincronización completada: {len(synced_employees)} usuarios sincronizados, {len(skipped_users)} omitidos, {len(failed_users)} fallidos",
            "total_users": len(all_users),
            "synced_count": len(synced_employees),
            "skipped_count": len(skipped_users),
            "failed_count": len(failed_users),
            "details": {
                "synced_users": [
                    {
                        "id": emp.id,
                        "user_id": emp.user_id,
                        "email": emp.email,
                        "full_name": emp.full_name,
                    }
                    for emp in synced_employees
                ],
                "skipped_users": skipped_users,
                "failed_users": failed_users,
            },
        }

