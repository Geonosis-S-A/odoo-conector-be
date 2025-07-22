from typing import List, Dict, Any, cast
from app.shared.infra.external.odoo.odoo_client import OdooConnection
from app.users.domain.repositories import EmployeeGateway
from app.users.domain.models import Employee


class OdooEmployeeGateway(EmployeeGateway):
    def __init__(self, odoo_client: OdooConnection) -> None:
        self.odoo_client = odoo_client

    def _transform_odoo_to_domain(self, odoo_data: Dict[str, Any]) -> Employee:
        """Transforma los datos de Odoo al modelo de dominio."""
        work_email = odoo_data.get("work_email")
        if not work_email or not isinstance(work_email, str) or "@" not in work_email:
            # Si no hay email válido, usamos un email temporal basado en el ID
            work_email = f"Carga_mi_mail_en_odoo_y_volve_a_sincronizar{odoo_data.get('id')}@temporary.com"

        employee_id = odoo_data.get("id")
        if not isinstance(employee_id, int):
            raise ValueError(f"ID de empleado inválido: {employee_id}")

        return Employee(
            id=employee_id,
            email=work_email,
            full_name=odoo_data.get("name", ""),
        )

    def get_user_roles_by_email(self, email: str) -> List[int] | None:
        """Obtiene los roles de un usuario de Odoo por su email."""
        try:
            # Buscar el usuario en res.users por email
            user_ids = cast(
                List[int],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "res.users",
                    "search",
                    [[["login", "=", email]]],
                ),
            )

            if not user_ids:
                return None

            # Obtener los datos del usuario incluyendo sus roles
            # Intentamos primero con 'groups_id', si falla probamos con 'group_ids'
            try:
                user_data = cast(
                    List[Dict[str, Any]],
                    self.odoo_client["models"].execute_kw(
                        self.odoo_client["ODOO_DB"],
                        self.odoo_client["uid"],
                        self.odoo_client["ODOO_PASSWORD"],
                        "res.users",
                        "read",
                        [user_ids[0:1]],  # Solo el primer usuario encontrado
                        {"fields": ["groups_id"]},
                    ),
                )
                field_name = "groups_id"
            except Exception as e:
                user_data = cast(
                    List[Dict[str, Any]],
                    self.odoo_client["models"].execute_kw(
                        self.odoo_client["ODOO_DB"],
                        self.odoo_client["uid"],
                        self.odoo_client["ODOO_PASSWORD"],
                        "res.users",
                        "read",
                        [user_ids[0:1]],  # Solo el primer usuario encontrado
                        {"fields": ["group_ids"]},
                    ),
                )
                field_name = "group_ids"

            if not user_data:
                return None

            # Extraer los IDs de los grupos/roles
            roles = cast(List[int], user_data[0].get(field_name, []))
            return roles

        except Exception as e:
            return None

    def get_all_users_with_roles(self) -> List[Dict[str, Any]]:
        """Obtiene todos los usuarios activos de Odoo con sus roles."""
        try:
            # Obtener usuarios activos con sus roles
            users = cast(
                List[Dict[str, Any]],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "res.users",
                    "search_read",
                    [[["active", "=", True]]],
                    {
                        "fields": ["id", "name", "login", "group_ids"],
                        "order": "name",
                    },
                ),
            )

            # Filtrar usuarios que también sean empleados
            user_employees = []
            for user in users:
                # Verificar si el usuario tiene un empleado asociado
                employee_ids = cast(
                    List[int],
                    self.odoo_client["models"].execute_kw(
                        self.odoo_client["ODOO_DB"],
                        self.odoo_client["uid"],
                        self.odoo_client["ODOO_PASSWORD"],
                        "hr.employee",
                        "search",
                        [[["user_id", "=", user["id"]]]],
                    ),
                )

                if employee_ids:
                    # Obtener datos del empleado
                    employee_data = cast(
                        List[Dict[str, Any]],
                        self.odoo_client["models"].execute_kw(
                            self.odoo_client["ODOO_DB"],
                            self.odoo_client["uid"],
                            self.odoo_client["ODOO_PASSWORD"],
                            "hr.employee",
                            "read",
                            [employee_ids[0:1]],
                            {"fields": ["id", "name", "work_email"]},
                        ),
                    )

                    if employee_data:
                        # Combinar datos del usuario y empleado
                        combined_data = {
                            "id": employee_data[0]["id"],  # ID del empleado
                            "name": employee_data[0]["name"],
                            "email": employee_data[0].get("work_email")
                            or user.get("login"),
                            "user_id": user["id"],  # ID del usuario para referencia
                            "roles": user.get("group_ids", [])
                            if isinstance(user.get("group_ids"), list)
                            else [],
                        }
                        user_employees.append(combined_data)

            return user_employees

        except Exception as e:
            print(f"Error al obtener usuarios con roles: {e}")
            return []

    def all(self) -> List[Employee]:
        """Obtiene todos los empleados de Odoo.

        Returns:
            List[Employee]: Lista de empleados transformados al modelo de dominio
        """
        odoo_employees = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "hr.employee",  # Modelo de empleados en Odoo
                "search_read",  # Método para buscar y leer registros
                [[]],  # Sin filtros (obtiene todos los empleados)
                {
                    "fields": ["id", "name", "work_email"],
                    "limit": 100,
                },
            ),
        )
        parsed_employees = [
            self._transform_odoo_to_domain(employee) for employee in odoo_employees
        ]
        return parsed_employees

    def exists_by_id(self, id: int) -> bool:
        """Verifica si un empleado existe en Odoo por su ID."""
        try:
            employee_data = cast(
                List[Dict[str, Any]],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "hr.employee",  # Modelo de empleados en Odoo
                    "search_read",
                    [[("id", "=", id)]],  # Buscar por ID específico
                    {"fields": ["id"], "limit": 1},
                ),
            )
            return len(employee_data) > 0
        except Exception:
            return False

    def get_by_email(self, email: str) -> Employee | None:
        # Primero buscar los IDs de empleados con el email dado
        employee_ids = cast(
            List[int],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "hr.employee",
                "search",
                [[["work_email", "=", email]]],
            ),
        )

        if not employee_ids:
            return None

        # Luego leer los datos completos del primer empleado encontrado
        employee_data = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "hr.employee",
                "read",
                [employee_ids[0:1]],  # Solo el primer ID encontrado
                {
                    "fields": ["id", "name", "work_email"],
                },
            ),
        )

        if not employee_data:
            return None

        return self._transform_odoo_to_domain(employee_data[0])
