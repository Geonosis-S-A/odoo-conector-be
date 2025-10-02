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
            email=work_email.lower(),
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
                    [[["login", "ilike", email]]],
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

    def get_by_id(self, id: int) -> Employee | None:
        """Obtiene un empleado por su ID."""
        employee_data = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "hr.employee",
                "read",
                [[id]],
                {"fields": ["id", "name", "work_email"]},
            ),
        )
        if not employee_data:
            return None
        return self._transform_odoo_to_domain(employee_data[0])

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
                [[["work_email", "ilike", email]]],
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

    def get_all_employees_with_user_data(self) -> List[Dict[str, Any]]:
        """
        Obtiene todos los empleados de Odoo con su información de usuario asociado.

        Para cada empleado retorna:
        - Datos básicos del empleado (id, name, email del hr.employee)
        - Si tiene user_id asociado y los roles correspondientes del res.users

        Returns:
            List[Dict]: Lista de empleados con su información de usuario
        """
        try:
            # 1. Obtener todos los empleados con campos básicos incluyendo user_id
            employees_data = cast(
                List[Dict[str, Any]],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "hr.employee",
                    "search_read",
                    [[]],  # Sin filtros (todos los empleados)
                    {
                        "fields": ["id", "name", "work_email", "user_id"],
                        "order": "name",
                    },
                ),
            )

            result = []

            # 2. Obtener todos los user_ids únicos que necesitamos consultar
            user_ids_to_fetch = []
            for employee in employees_data:
                user_id = employee.get("user_id")
                if user_id and isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                    actual_user_id = user_id[0] if isinstance(user_id[0], int) else None
                    if actual_user_id and actual_user_id not in user_ids_to_fetch:
                        user_ids_to_fetch.append(actual_user_id)

            # 3. Obtener datos de usuarios con roles en una sola consulta
            users_data = {}
            if user_ids_to_fetch:
                users_info = cast(
                    List[Dict[str, Any]],
                    self.odoo_client["models"].execute_kw(
                        self.odoo_client["ODOO_DB"],
                        self.odoo_client["uid"],
                        self.odoo_client["ODOO_PASSWORD"],
                        "res.users",
                        "read",
                        [user_ids_to_fetch],
                        {"fields": ["id", "login", "group_ids"]},
                    ),
                )

                # Crear un diccionario para acceso rápido por user_id
                users_data = {user["id"]: user for user in users_info}

            # 4. Procesar cada empleado y combinar con datos de usuario
            for employee in employees_data:
                employee_result = {
                    "id": employee["id"],
                    "name": employee.get("name", ""),
                    "email": employee.get("work_email", ""),
                    "user_id": None,
                    "has_user": False,
                    "roles": [],
                }

                # Verificar si tiene user_id asociado
                user_id = employee.get("user_id")
                if user_id and isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                    actual_user_id = user_id[0] if isinstance(user_id[0], int) else None

                    if actual_user_id and actual_user_id in users_data:
                        user_info = users_data[actual_user_id]
                        employee_result.update(
                            {
                                "user_id": actual_user_id,
                                "has_user": True,
                                "roles": user_info.get("group_ids", [])
                                if isinstance(user_info.get("group_ids"), list)
                                else [],
                            }
                        )

                result.append(employee_result)

            return result

        except Exception as e:
            print(f"Error al obtener empleados con datos de usuario: {e}")
            return []

    def get_employee_with_user_data(self, employee_id: int) -> Dict[str, Any] | None:
        """
        Obtiene los datos de un empleado por ID, incluyendo información de usuario si existe.

        - Nombre y email: siempre del modelo hr.employee
        - Roles: solo si el empleado tiene user_id, del modelo res.users

        Args:
            employee_id: ID del empleado en Odoo

        Returns:
            Dict con datos del empleado y usuario (si existe), o None si no se encuentra
        """
        try:
            # 1. Buscar el empleado por ID en hr.employee (nombre y email provienen de aquí)
            employee_data = cast(
                List[Dict[str, Any]],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "hr.employee",
                    "read",
                    [[employee_id]],
                    {"fields": ["id", "name", "work_email", "user_id"]},
                ),
            )

            if not employee_data:
                return None

            employee = employee_data[0]

            # 2. Preparar datos básicos del empleado (nombre y email del hr.employee)
            result = {
                "id": employee["id"],
                "name": employee.get("name", ""),  # Del hr.employee
                "email": employee.get("work_email", ""),  # Del hr.employee
                "user_id": None,
                "has_user": False,
                "roles": [],
            }

            # 3. Si el empleado tiene user_id asociado, obtener roles del res.users
            user_id = employee.get("user_id")
            if user_id and isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                # user_id viene como [id, nombre] de Odoo
                actual_user_id = user_id[0] if isinstance(user_id[0], int) else None

                if actual_user_id:
                    # Obtener datos del usuario incluyendo roles del res.users
                    # Intentar con ambos nombres de campo posibles según el entorno de Odoo
                    user_data = None
                    groups_field = None

                    # Primero intentar con 'groups_id'
                    try:
                        user_data = cast(
                            List[Dict[str, Any]],
                            self.odoo_client["models"].execute_kw(
                                self.odoo_client["ODOO_DB"],
                                self.odoo_client["uid"],
                                self.odoo_client["ODOO_PASSWORD"],
                                "res.users",
                                "read",
                                [[actual_user_id]],
                                {"fields": ["id", "login", "groups_id"]},
                            ),
                        )
                        groups_field = "groups_id"
                    except Exception:
                        # Si falla, intentar con 'group_ids'
                        try:
                            user_data = cast(
                                List[Dict[str, Any]],
                                self.odoo_client["models"].execute_kw(
                                    self.odoo_client["ODOO_DB"],
                                    self.odoo_client["uid"],
                                    self.odoo_client["ODOO_PASSWORD"],
                                    "res.users",
                                    "read",
                                    [[actual_user_id]],
                                    {"fields": ["id", "login", "group_ids"]},
                                ),
                            )
                            groups_field = "group_ids"
                        except Exception as e:
                            print(
                                f"Error al obtener datos del usuario {actual_user_id}: {e}"
                            )

                    if user_data and groups_field:
                        user = user_data[0]
                        groups = user.get(groups_field, [])
                        result.update(
                            {
                                "user_id": actual_user_id,
                                "has_user": True,
                                "roles": groups if isinstance(groups, list) else [],
                            }
                        )

            return result

        except Exception as e:
            print(f"Error al obtener empleado {employee_id}: {e}")
            return None

    def get_user_id_by_employee_id(self, employee_id: int) -> int | None:
        """
        Obtiene el user_id asociado a un employee_id en Odoo.

        Args:
            employee_id: ID del empleado en Odoo

        Returns:
            int: user_id asociado al empleado, o None si no se encuentra o no tiene usuario asociado
        """
        try:
            # Buscar el empleado por ID y obtener solo el campo user_id
            employee_data = cast(
                List[Dict[str, Any]],
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "hr.employee",
                    "read",
                    [[employee_id]],
                    {"fields": ["user_id"]},
                ),
            )

            if not employee_data:
                return None

            employee = employee_data[0]
            user_id = employee.get("user_id")

            # user_id viene como [id, nombre] de Odoo o False si no tiene usuario asociado
            if user_id and isinstance(user_id, (list, tuple)) and len(user_id) > 0:
                actual_user_id = user_id[0] if isinstance(user_id[0], int) else None
                return actual_user_id

            return None

        except Exception as e:
            return None
