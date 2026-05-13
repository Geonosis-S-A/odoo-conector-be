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

    _INTERNAL_PROJECT_EXCLUSION = [3, 1, 87, 2]

    def _build_timesheet_domain(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        project_id: Optional[int] = None,
        validated: Optional[bool] = None,
        team: Optional[bool] = None,
        user_id: Optional[int] = None,
        team_members_ids: Optional[list[int]] = None,
    ) -> list[tuple[str, str, Any]]:
        """Construye el dominio Odoo para listados / conteos de líneas de timesheet."""
        domain: list[tuple[str, str, Any]] = [("is_timesheet", "=", True)]
        if date_from is not None:
            domain.append(("date", ">=", date_from.isoformat()))

        if date_to is not None:
            domain.append(("date", "<=", date_to.isoformat()))

        if project_id is not None:
            domain.append(("project_id", "=", project_id))

        if validated is not None:
            domain.append(("validated", "=", validated))
        if employee_id is not None and team is None:
            domain.append(("employee_id", "=", employee_id))

        domain.append(("project_id", "not in", self._INTERNAL_PROJECT_EXCLUSION))

        if team and user_id is not None and team_members_ids is not None:
            domain.append(("employee_id", "in", team_members_ids))

        return domain

    def count(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        project_id: Optional[int] = None,
        validated: Optional[bool] = None,
        team: Optional[bool] = None,
        user_id: Optional[int] = None,
        team_members_ids: Optional[list[int]] = None,
    ) -> int:
        domain = self._build_timesheet_domain(
            employee_id,
            date_from,
            date_to,
            project_id,
            validated,
            team,
            user_id,
            team_members_ids,
        )
        return int(
            cast(
                int,
                self.odoo_client["models"].execute_kw(
                    self.odoo_client["ODOO_DB"],
                    self.odoo_client["uid"],
                    self.odoo_client["ODOO_PASSWORD"],
                    "account.analytic.line",
                    "search_count",
                    [domain],
                ),
            )
        )

    def all(
        self,
        employee_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        project_id: Optional[int] = None,
        validated: Optional[bool] = None,
        team: Optional[bool] = None,
        user_id: Optional[int] = None,
        team_members_ids: Optional[list[int]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[DetailedTimesheetLine]:
        """Obtiene líneas de hoja de tiempo de Odoo.

        Opcionalmente aplica limit/offset en Odoo (VT-08, pentest 2026-04).
        """
        domain = self._build_timesheet_domain(
            employee_id,
            date_from,
            date_to,
            project_id,
            validated,
            team,
            user_id,
            team_members_ids,
        )

        opts: dict[str, Any] = {
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
            "order": "date desc, id desc",
        }
        if limit is not None:
            opts["limit"] = limit
        if offset is not None:
            opts["offset"] = offset

        odoo_timesheet_lines = cast(
            List[Dict[str, Any]],
            self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "account.analytic.line",
                "search_read",
                [domain],
                opts,
            ),
        )

        parsed_lines = [
            self._transform_odoo_to_detailed_domain(line)
            for line in odoo_timesheet_lines
        ]
        return parsed_lines

    def all_by_employees(
        self,
        employee_ids: list[int],
        date_from: date,
        date_to: date,
    ) -> List[Dict[str, Any]]:
        """Obtiene todas las líneas de hoja de tiempo de Odoo por empleados."""
        domain = [
            ("employee_id", "in", employee_ids),
            ("date", ">=", date_from.isoformat()),
            ("date", "<=", date_to.isoformat()),
        ]
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
        return odoo_timesheet_lines

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

    def get_team_users(self, user_id: int, employee_id: int) -> list[Dict[str, Any]]:
        """
        Obtiene la cantidad de usuarios activos en el equipo consultando directamente a Odoo.
        """
        try:
            # Construir dominio para obtener empleados del equipo que estén activos
            subordinates_domain = [
                # Condición 1: El empleado NO debo ser yo
                ("id", "!=", employee_id),
                # Condición 2: Y debe cumplir la lógica de equipo
                "|",
                ("timesheet_manager_id", "=", user_id),
                ("id", "child_of", employee_id),
            ]

            # Contar empleados que cumplen el criterio
            subordinates_data = self.odoo_client["models"].execute_kw(
                self.odoo_client["ODOO_DB"],
                self.odoo_client["uid"],
                self.odoo_client["ODOO_PASSWORD"],
                "hr.employee",  # Estamos buscando en el modelo de empleados
                "search_read",  # El método que busca Y lee los datos
                [subordinates_domain],  # El filtro se pasa como una lista de argumentos
                {
                    # El diccionario de opciones donde especificamos qué queremos
                    "fields": [
                        "id",  # El ID del empleado (el "employee_id" que buscas)
                        "name",  # El nombre completo del empleado
                        "work_email",
                    ],
                    # "limit": 100 # Opcional: para limitar el número de resultados
                },
            )

            return subordinates_data

        except Exception as e:
            raise Exception(
                f"Error al obtener cantidad de usuarios del equipo: {str(e)}"
            )

    def get_by_task_or_project(
        self,
        task_id: Optional[int] = None,
        project_id: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> List[DetailedTimesheetLine]:
        """
        Obtiene líneas de timesheet filtradas por tarea o proyecto en un período específico.

        Args:
            task_id: ID de la tarea a filtrar (opcional)
            project_id: ID del proyecto a filtrar (opcional, usado cuando task_id es None)
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            Lista de DetailedTimesheetLine que coinciden con los criterios
        """
        try:
            # Validar que al menos uno de los parámetros de filtro esté presente
            if not task_id and not project_id:
                raise ValueError("Debe proporcionar task_id o project_id")

            if not date_from or not date_to:
                raise ValueError("Debe proporcionar date_from y date_to")

            # Construir dominio de filtros para Odoo
            domain = [
                ("is_timesheet", "=", True),
                ("date", ">=", date_from.isoformat()),
                ("date", "<=", date_to.isoformat()),
            ]

            # Filtrar por tarea específica si se proporciona task_id
            if task_id:
                domain.append(("task_id", "=", task_id))
            # Si no hay task_id, filtrar por proyecto Y solo líneas sin tarea
            elif project_id:
                domain.extend(
                    [
                        ("project_id", "=", project_id),
                        ("task_id", "=", False),  # Solo líneas sin tarea asignada
                    ]
                )

            # Hacer consulta directa a Odoo
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

            # Transformar datos de Odoo a nuestro modelo de dominio
            parsed_lines = []
            if odoo_timesheet_lines:
                parsed_lines = [
                    self._transform_odoo_to_detailed_domain(line)
                    for line in odoo_timesheet_lines
                ]

            return parsed_lines

        except Exception as e:
            raise Exception(f"Error al obtener timesheet por tarea/proyecto: {str(e)}")

    def all_by_employees_with_requester_user_id(
        self,
        employee_ids: list[int],
        date_from: date,
        date_to: date,
        requester_user_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Obtiene líneas de timesheet que cumplen una de estas condiciones:
        1. Pertenecen a empleados específicos (employee_ids)
        2. Pertenecen a proyectos donde requester_user_id es gerente
        """
        # Primero obtenemos los proyectos donde el requester_user_id es gerente
        managed_projects = self.odoo_client["models"].execute_kw(
            self.odoo_client["ODOO_DB"],
            self.odoo_client["uid"],
            self.odoo_client["ODOO_PASSWORD"],
            "project.project",
            "search",
            [
                [("user_id", "=", requester_user_id)]
            ],  # user_id es el campo para el gerente del proyecto
        )

        # Construir dominio con lógica OR correcta
        domain = [
            # Condiciones de fecha (obligatorias)
            ("date", ">=", date_from.isoformat()),
            ("date", "<=", date_to.isoformat()),
            # Condición OR: empleados específicos O proyectos gestionados
            "|",
            ("employee_id", "in", employee_ids),
            ("project_id", "in", managed_projects),
        ]
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
        return odoo_timesheet_lines
