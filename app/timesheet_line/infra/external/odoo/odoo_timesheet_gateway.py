from typing import List, Dict, Any, Optional, cast
from datetime import datetime, date
from app.timesheet_line.domain.models import DetailedTimesheetLine, TimesheetLine
from app.task.domain.models import TaskInfo
from app.project.domain.models import Project
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.shared.infra.external.odoo.odoo_client import OdooConnection


class OdooTimesheetLineGateway(TimesheetLineGateway):
    def __init__(self, odoo_client: OdooConnection) -> None:
        self.odoo_client = odoo_client

    def _transform_odoo_to_detailed_domain(
        self, odoo_data: Dict[str, Any]
    ) -> DetailedTimesheetLine:
        """Transforma los datos de Odoo al modelo de dominio."""
        # Odoo devuelve la fecha como string, por ejemplo "2024-05-19"
        date_str = odoo_data.get("date")
        if not date_str:
            raise ValueError("La fecha es obligatoria para la línea de hoja de tiempo")

        date_obj: date = datetime.strptime(date_str, "%Y-%m-%d").date()

        # Odoo devuelve los IDs como tuplas [id, nombre] o False si está vacío
        task: TaskInfo | None = None
        raw_task_id = odoo_data.get("task_id")
        if raw_task_id is None or raw_task_id is False:
            task = None
        elif isinstance(raw_task_id, list) and len(raw_task_id) > 0:
            # Obtener información del proyecto para el task
            project_id = 0
            project_name = ""
            raw_project_id = odoo_data.get("project_id", False)
            if isinstance(raw_project_id, list) and len(raw_project_id) > 0:
                project_id = raw_project_id[0]
                project_name = raw_project_id[1]

            task = TaskInfo(
                id=raw_task_id[0],
                name=raw_task_id[1],
                project_id=project_id,
                project_name=project_name,
            )

        # Manejar employee_id que puede ser False o [id, nombre]
        employee_id = 0
        raw_employee_id = odoo_data.get("employee_id", False)
        if isinstance(raw_employee_id, list) and len(raw_employee_id) > 0:
            employee_id = raw_employee_id[0]
        elif isinstance(raw_employee_id, (int, str)):
            employee_id = int(raw_employee_id)

        # Manejar project_id que puede ser False o [id, nombre]
        project_id = 0
        project_name = ""
        raw_project_id = odoo_data.get("project_id", False)
        if isinstance(raw_project_id, list) and len(raw_project_id) > 0:
            project_id = raw_project_id[0]
            project_name = raw_project_id[1]
        elif isinstance(raw_project_id, (int, str)):
            project_id = int(raw_project_id)

        if odoo_data.get("id") is None:
            raise ValueError("El ID de la línea de hoja de tiempo es requerido")

        if odoo_data.get("name") is None:
            raise ValueError("El nombre de la línea de hoja de tiempo es requerido")

        return DetailedTimesheetLine(
            id=odoo_data.get("id"),
            name=odoo_data.get("name"),
            employee_id=employee_id,
            project=Project(
                id=project_id,
                name=project_name,
            ),
            hours=float(odoo_data.get("unit_amount", 0.0)),
            date=date_obj,
            task=task,
            create_date=odoo_data.get("create_date", None),
            validated=odoo_data.get("validated", False),
        )

    def create(self, timesheet_lines: list[TimesheetLine]) -> list[int] | None:
        """Crea múltiples líneas de hoja de tiempo en Odoo usando batch create.

        Args:
            timesheet_lines: Lista de líneas de hoja de tiempo a crear

        Returns:
            list[int]: Lista de IDs de las líneas creadas
        """
        # Preparar todos los datos para el batch create
        timesheet_entries = []

        for timesheet_line in timesheet_lines:
            odoo_data = {
                "date": timesheet_line.date.isoformat(),
                "unit_amount": timesheet_line.hours,
                "employee_id": timesheet_line.employee_id,
                "project_id": timesheet_line.project_id,
            }

            # Solo agregamos task_id si no es None
            if timesheet_line.task_id is not None:
                odoo_data["task_id"] = timesheet_line.task_id

            if timesheet_line.name is not None:
                odoo_data["name"] = timesheet_line.name

            timesheet_entries.append(odoo_data)

        # Batch create: todo en una sola llamada
        odoo_timesheet_ids: list[int] = cast(
            list[int],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",  # Modelo de las líneas de hojas de tiempo
                "create",  # Método para crear registros
                [timesheet_entries],  # Lista de datos para crear en batch
            ),
        )
        return odoo_timesheet_ids

    def all(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        project_id: Optional[int] = None,
        validated: Optional[bool] = None,
        team: Optional[bool] = None,
        user_id: Optional[int] = None,
    ) -> List[DetailedTimesheetLine]:
        """Obtiene todas las líneas de hoja de tiempo de Odoo."""
        domain: list[tuple[str, str, Any]] = [("is_timesheet", "=", True)]
        # Condición base
        if date_from is not None:
            domain.append(("date", ">=", date_from.isoformat()))

        if date_to is not None:
            domain.append(("date", "<=", date_to.isoformat()))

        if project_id is not None:
            domain.append(("project_id", "=", project_id))

        if validated is not None:
            domain.append(("validated", "=", validated))
        if employee_id is not None:
            domain.append(("employee_id", "=", employee_id))

        if team and user_id is not None:
            # Aquí aplicamos el filtro de equipo como se ve en la petición web
            team_domain = [
                "|",
                "|",
                ("employee_id.timesheet_manager_id", "=", user_id),
                ("employee_id.parent_id.user_id", "=", user_id),
                ("employee_id.is_subordinate", "=", True),
            ]
            domain.extend(team_domain)

        odoo_timesheet_lines = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",
                "search_read",
                [domain],
                {
                    "fields": [
                        "name",
                        "date",
                        "unit_amount",
                        "employee_id",
                        "project_id",
                        "task_id",
                        "create_date",
                        "validated",
                    ],
                },
            ),
        )
        parsed_lines = [
            self._transform_odoo_to_detailed_domain(line)
            for line in odoo_timesheet_lines
        ]
        return parsed_lines

    def delete(self, timesheet_lines_ids: list[int]) -> bool:
        """Elimina líneas de hoja de tiempo de Odoo.

        Args:
            timesheet_lines_ids: Lista de IDs de las líneas de hoja de tiempo a eliminar

        Returns:
            bool: True si la eliminación fue exitosa, False en caso contrario
        """

        response = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "account.analytic.line",
            "unlink",  # Método de Odoo para eliminar registros
            [timesheet_lines_ids],  # Corregido: un solo nivel de array
        )
        if response:
            return True
        else:
            return False

    def update(self, timesheet_line: TimesheetLine) -> bool:
        """Actualiza una línea de hoja de tiempo en Odoo.

        Args:
            timesheet_line: La línea de hoja de tiempo a actualizar

        Returns:
            bool: True si la actualización fue exitosa, False en caso contrario
        """
        if not timesheet_line.id:
            raise ValueError(
                "El ID de la línea de hoja de tiempo es requerido para actualizar"
            )

        odoo_data = {
            "name": timesheet_line.name,
            "date": timesheet_line.date.isoformat(),
            "unit_amount": timesheet_line.hours,
            "employee_id": timesheet_line.employee_id,
            "project_id": timesheet_line.project_id,
        }

        # Solo agregamos task_id si no es None
        if timesheet_line.task_id is not None:
            odoo_data["task_id"] = timesheet_line.task_id

        response = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "account.analytic.line",
            "write",
            [[timesheet_line.id], odoo_data],
        )

        if response:
            return True
        else:
            return False

    def get_by_id(self, timesheet_line_id: int) -> DetailedTimesheetLine | None:
        """Obtiene una línea de hoja de tiempo por su ID.

        Args:
            timesheet_line_id: ID de la línea de hoja de tiempo a obtener

        Returns:
            DetailedTimesheetLine: Línea de hoja de tiempo con detalles
        """

        odoo_data = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",
                "read",
                [timesheet_line_id],
                {
                    "fields": [
                        "id",
                        "name",
                        "date",
                        "unit_amount",
                        "employee_id",
                        "project_id",
                        "task_id",
                        "create_date",
                        "validated",
                    ],
                },
            ),
        )
        if not odoo_data or len(odoo_data) == 0:
            return None
        return self._transform_odoo_to_detailed_domain(odoo_data[0])

    def get_by_ids(self, timesheet_line_ids: list[int]) -> list[DetailedTimesheetLine]:
        """Obtiene múltiples líneas de hoja de tiempo por sus IDs.

        Args:
            timesheet_line_ids: Lista de IDs de las líneas de hoja de tiempo a obtener

        Returns:
            list[DetailedTimesheetLine]: Lista de líneas de hoja de tiempo con detalles
        """
        if not timesheet_line_ids:
            return []

        odoo_data = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",
                "read",
                [timesheet_line_ids],  # Lista de IDs para buscar
                {
                    "fields": [
                        "id",
                        "name",
                        "date",
                        "unit_amount",
                        "employee_id",
                        "project_id",
                        "task_id",
                        "create_date",
                        "validated",
                    ],
                },
            ),
        )

        if not odoo_data:
            return []

        # Transformar todos los datos de Odoo al modelo de dominio
        return [
            self._transform_odoo_to_detailed_domain(line_data)
            for line_data in odoo_data
        ]

    def validate(self, timesheet_line_ids: list[int]) -> bool:
        """Valida múltiples líneas de hoja de tiempo en Odoo (marca validated=True).

        Args:
            timesheet_line_ids: Lista de IDs de las líneas de hoja de tiempo a validar

        Returns:
            bool: True si la validación fue exitosa, False en caso contrario
        """
        if not timesheet_line_ids:
            return True

        response = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "account.analytic.line",
            "action_validate_timesheet",
            [timesheet_line_ids],
            {},
        )

        return bool(response)

    def get_timesheet_data_by_team(
        self,
        user_id: int,
        employee_id: int,
        date_from: date,
        date_to: date,
    ) -> List[Dict[str, Any]]:
        """Obtiene datos de timesheet del equipo."""
        domain = [
            ("is_timesheet", "=", True),
            ("date", ">=", date_from.isoformat()),
            ("date", "<=", date_to.isoformat()),
            # --- Condición para excluirte ---
            # El operador AND es implícito al agregar una nueva tupla
            ("employee_id", "!=", employee_id),
            # Filtro de equipo:
            #  - El timesheet manager del empleado soy yo
            #  - O el empleado está por debajo de mí en el organigrama
            "|",
            ("employee_id.timesheet_manager_id", "=", user_id),
            ("employee_id", "child_of", employee_id),
        ]

        # Ejecutar consulta a Odoo
        response = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",
                "search_read",
                [domain],
                {
                    "fields": [
                        "name",
                        "date",
                        "unit_amount",
                        "employee_id",
                        "project_id",
                        "task_id",
                        "create_date",
                        "validated",
                    ],
                },
            ),
        )
        return response

    def get_active_team_users_count(self, user_id: int) -> int:
        """
        Obtiene la cantidad de usuarios activos en el equipo consultando directamente a Odoo.
        """
        try:
            # Construir dominio para obtener empleados del equipo que estén activos
            domain = [
                "|",
                ("timesheet_manager_id", "=", user_id),
                "|",
                ("parent_id.user_id", "=", user_id),
                ("is_subordinate", "=", True),
            ]

            # Contar empleados que cumplen el criterio
            employee_count = cast(
                int,
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "hr.employee",
                    "search_count",
                    [domain],
                ),
            )

            return employee_count

        except Exception as e:
            raise Exception(
                f"Error al obtener cantidad de usuarios del equipo: {str(e)}"
            )
