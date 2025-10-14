from datetime import date
from typing import List, Optional, Dict, Any
from collections import defaultdict

from app.dashboard.domain.models import DashboardSummary, KPI
from app.dashboard.domain.repositories import DashboardDataService
from app.users.domain.repositories import EmployeeGateway
from app.task.domain.gateway import TaskGateway
from app.timesheet_line.domain.repositories import TimesheetLineGateway
from app.employee_price.domain.repositories import EmployeePriceRepository
from app.employee_price.domain.models import EmployeePrice


class GetDashboardSummaryUseCase:
    """Caso de uso para obtener el resumen del dashboard del equipo."""

    def __init__(
        self,
        dashboard_service: DashboardDataService,
        employee_gateway: EmployeeGateway,
        task_gateway: TaskGateway,
        timesheet_line_gateway: TimesheetLineGateway,
        employee_price_repository: EmployeePriceRepository,
    ):
        self.dashboard_service = dashboard_service
        self.employee_gateway = employee_gateway
        self.task_gateway = task_gateway
        self.timesheet_line_gateway = timesheet_line_gateway
        self.employee_price_repository = employee_price_repository

    def execute(
        self, user_id: int, employee_id: int, date_from: date, date_to: date
    ) -> DashboardSummary:
        """
        Ejecuta el caso de uso para obtener el resumen del dashboard.

        Args:
            user_id: ID del usuario que solicita el dashboard
            date_from: Fecha de inicio del período
            date_to: Fecha de fin del período

        Returns:
            DashboardSummary con todos los KPIs y totales calculados
        """

        team_users = self.timesheet_line_gateway.get_team_users(user_id, employee_id)

        ids = [user["id"] for user in team_users]

        timesheet_data = self.dashboard_service.get_timesheet_summary(
            ids,
            date_from,
            date_to,
            self.task_gateway,
            self.timesheet_line_gateway,
            user_id,
        )

        # Calcular empleados únicos que realmente cargaron horas
        # Esto incluye empleados del equipo + empleados externos que trabajaron en proyectos gestionados
        unique_employee_ids = set(record.employee_id for record in timesheet_data)
        users_count = len(unique_employee_ids)

        # 2.1. Obtener precios solo para empleados únicos y construir índice
        employee_prices = self.employee_price_repository.get_by_user_ids(
            list(unique_employee_ids)
        )
        price_index = self._build_price_index(employee_prices)

        # Opcional: Calcular costos para cada timesheet line
        # timesheet_costs se puede usar para cálculos de facturación o reportes
        timesheet_costs = []
        for ts_line in timesheet_data:
            cost_per_hour = self._get_cost_for_date(
                ts_line.employee_id, ts_line.date, price_index
            )
            total_cost = (ts_line.hours * cost_per_hour) if cost_per_hour else None

            timesheet_costs.append(
                {
                    "timesheet_line": ts_line,
                    "cost_per_hour": cost_per_hour,
                    "total_cost": total_cost,
                }
            )

        # 3. Calcular KPIs reales
        hours_kpi = self.dashboard_service.calculate_hours_kpi(
            timesheet_data, users_count
        )
        entries_kpi = self.dashboard_service.calculate_entries_kpi(
            timesheet_data, users_count
        )
        daily_average_kpi = self.dashboard_service.calculate_daily_average_kpi(
            timesheet_data, users_count, date_from, date_to
        )

        # 3.1. Calcular KPI de costo total
        total_cost_kpi = self._calculate_total_cost_kpi(timesheet_costs, users_count)

        # 4. Calcular totales desagregados
        by_project = self.dashboard_service.calculate_project_totals(timesheet_data)
        by_task = self.dashboard_service.calculate_task_totals(timesheet_data)

        # 4.1. Crear mapa de costos de timesheets para cálculos
        timesheet_cost_map = {
            cost_data["timesheet_line"].id: cost_data["total_cost"]
            for cost_data in timesheet_costs
            if cost_data["total_cost"] is not None
        }

        by_employee = self.dashboard_service.calculate_employee_totals(
            timesheet_data, team_users, timesheet_cost_map
        )

        # 5. Calcular horas cargadas a proyectos sin tarea específica
        by_project_without_task = (
            self.dashboard_service.calculate_project_without_task_totals(
                by_project, by_task
            )
        )

        "append de by_project_without_task a by_task"
        by_task.extend(by_project_without_task)

        # 6. Calcular nueva estructura jerárquica con costos
        # Usar el mismo timesheet_cost_map creado anteriormente
        hierarchical_summary = self.dashboard_service.calculate_hierarchical_summary(
            timesheet_data, self.task_gateway, timesheet_cost_map
        )

        # 7. Crear y retornar el resumen del dashboard
        dashboard_summary = DashboardSummary.create(
            users_count=users_count,
            hours_selected_period=hours_kpi,
            entries_selected_period=entries_kpi,
            daily_average_hours=daily_average_kpi,
            by_project=by_project,
            by_task=by_task,
            by_employee=by_employee,
            hierarchical_summary=hierarchical_summary,
            total_cost=total_cost_kpi,
        )

        return dashboard_summary

    def _calculate_total_cost_kpi(
        self, timesheet_costs: List[Dict[str, Any]], users_count: int
    ) -> Optional[KPI]:
        """
        Calcula el KPI de costo total del período.

        Args:
            timesheet_costs: Lista de timesheets con información de costos
            users_count: Cantidad de usuarios únicos

        Returns:
            KPI con el costo total y promedio por usuario, o None si no hay datos
        """
        # Filtrar solo los costos que tienen valor
        valid_costs = [
            ts["total_cost"] for ts in timesheet_costs if ts["total_cost"] is not None
        ]

        if not valid_costs:
            # Si no hay costos calculados, retornar None
            return None

        total_cost = sum(valid_costs)
        average_per_user = total_cost / users_count if users_count > 0 else 0

        return KPI(
            total=round(total_cost, 2),
            average_per_user=round(average_per_user, 2),
            unit="currency",
        )

    def _build_price_index(
        self, employee_prices: List[EmployeePrice]
    ) -> dict[int, list[EmployeePrice]]:
        """
        Construye un índice de precios agrupados por employee_id.

        Args:
            employee_prices: Lista de precios de empleados

        Returns:
            Diccionario con user_id como clave y lista de precios como valor
        """
        index = defaultdict(list)
        for price in employee_prices:
            index[price.user_id].append(price)
        return index

    def _get_cost_for_date(
        self,
        employee_id: int,
        check_date: date,
        price_index: dict[int, list[EmployeePrice]],
    ) -> Optional[float]:
        """
        Obtiene el costo por hora vigente para un empleado en una fecha específica.
        Si no hay precio vigente, retorna el más cercano anterior.
        Si no hay anteriores, retorna el más cercano futuro.

        Args:
            employee_id: ID del empleado
            check_date: Fecha a verificar
            price_index: Índice de precios pre-construido

        Returns:
            Costo por hora si existe un precio vigente o cercano, None si no hay precios
        """
        prices = price_index.get(employee_id, [])

        if not prices:
            return None

        # 1. Primero buscar precio vigente en la fecha exacta
        for price in prices:
            if price.is_active_on(check_date):
                return price.cost_per_hour

        # 2. Si no hay precio vigente, buscar el más cercano anterior
        # Filtrar precios que empezaron antes o en la fecha
        previous_prices = [p for p in prices if p.date_from <= check_date]

        if previous_prices:
            # Ordenar por date_from descendente y tomar el más reciente
            closest = max(previous_prices, key=lambda p: p.date_from)
            return closest.cost_per_hour

        # 3. Si no hay precios anteriores, tomar el más próximo futuro
        future_prices = [p for p in prices if p.date_from > check_date]

        if future_prices:
            # Tomar el que empieza más pronto
            closest = min(future_prices, key=lambda p: p.date_from)
            return closest.cost_per_hour

        return None
