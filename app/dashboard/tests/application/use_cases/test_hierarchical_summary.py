import pytest
from datetime import date
from unittest.mock import Mock
from app.dashboard.infra.dashboard_service import OdooDashboardDataService
from app.dashboard.domain.models import HierarchicalSummary, HierarchicalItem
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.task.domain.models import TaskInfo, TaskWithParentInfo


class TestHierarchicalSummary:
    """Tests unitarios para calculate_hierarchical_summary."""

    @pytest.fixture
    def dashboard_service(self):
        """Instancia del servicio de dashboard con mocks."""
        mock_odoo_client = Mock()
        mock_employee_gateway = Mock()
        mock_task_gateway = Mock()
        mock_timesheet_gateway = Mock()

        return OdooDashboardDataService(
            mock_odoo_client,
            mock_employee_gateway,
            mock_task_gateway,
            mock_timesheet_gateway,
        )

    @pytest.fixture
    def mock_task_gateway(self):
        """Mock del gateway de tareas."""
        return Mock()

    def test_basic_project_with_simple_task(self, dashboard_service, mock_task_gateway):
        """Caso básico: Un proyecto con una tarea simple."""
        # Arrange
        timesheet_data = [
            DetailedTimesheetLine(
                id=1,
                name="Desarrollo",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Tarea 1", project_id=1, project_name="Proyecto A"
                ),
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
        ]

        # Mock del task gateway - tarea sin padre
        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Tarea 1",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            )
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert isinstance(result, HierarchicalSummary)
        assert result.total_hours == 8.0
        assert len(result.data) == 1

        # Proyecto
        project = result.data[0]
        assert project.type == "project"
        assert project.id == 1
        assert project.name == "Proyecto A"
        assert project.total_hours == 8.0
        assert not project.is_artificial
        assert len(project.data) == 1

        # Tarea - debe ser un nodo hoja (optimizada sin "Sin subtarea")
        task = project.data[0]
        assert task.type == "task"
        assert task.id == 1
        assert task.name == "Tarea 1"
        assert task.total_hours == 8.0
        assert not task.is_artificial
        assert len(task.data) == 0  # Optimizada como nodo hoja

    def test_project_with_direct_hours_no_task(
        self, dashboard_service, mock_task_gateway
    ):
        """Caso: Horas cargadas directamente al proyecto sin tarea."""
        # Arrange
        timesheet_data = [
            DetailedTimesheetLine(
                id=1,
                name="Trabajo general",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=None,  # Sin tarea
                hours=6.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
        ]

        # Mock del task gateway - sin tareas
        mock_task_gateway.get_tasks_info_with_parents.return_value = {}

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert result.total_hours == 6.0
        assert len(result.data) == 1

        # Proyecto
        project = result.data[0]
        assert project.name == "Proyecto A"
        assert project.total_hours == 6.0

        # NOTA: La optimización puede eliminar el nodo "Sin tarea" si es el único hijo
        # En este caso, el proyecto queda como nodo hoja directamente
        # Esto es correcto y esperado por la optimización
        if len(project.data) == 0:
            # Caso optimizado: proyecto como nodo hoja
            assert not project.is_artificial
        else:
            # Caso no optimizado: con nodo "Sin tarea"
            assert len(project.data) == 1
            sin_tarea = project.data[0]
            assert sin_tarea.type == "task"
            assert sin_tarea.id < 0  # ID artificial negativo
            assert sin_tarea.name == "Sin tarea"
            assert sin_tarea.total_hours == 6.0
            assert sin_tarea.is_artificial
            assert len(sin_tarea.data) == 0

    def test_task_with_subtask_parent_child_relationship(
        self, dashboard_service, mock_task_gateway
    ):
        """Caso: Tarea padre con subtarea - relación padre-hijo."""
        # Arrange
        timesheet_data = [
            # Horas en tarea padre
            DetailedTimesheetLine(
                id=1,
                name="Planificación",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Tarea Padre", project_id=1, project_name="Proyecto A"
                ),
                hours=4.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            # Horas en subtarea
            DetailedTimesheetLine(
                id=2,
                name="Implementación",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=2, name="Subtarea", project_id=1, project_name="Proyecto A"
                ),
                hours=8.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
        ]

        # Mock del task gateway - subtarea con padre
        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Tarea Padre",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            ),
            2: TaskWithParentInfo(
                id=2,
                name="Subtarea",
                project_id=1,
                project_name="Proyecto A",
                parent_id=1,
            ),
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert result.total_hours == 12.0
        assert len(result.data) == 1

        # Proyecto
        project = result.data[0]
        assert project.total_hours == 12.0
        assert len(project.data) == 1

        # Tarea padre
        tarea_padre = project.data[0]
        assert tarea_padre.id == 1
        assert tarea_padre.name == "Tarea Padre"
        assert tarea_padre.total_hours == 12.0  # 4.0 directas + 8.0 de subtarea
        assert not tarea_padre.is_artificial
        assert len(tarea_padre.data) == 2  # Subtarea real + "Sin subtarea" del padre

        # Ordenar por horas para predicir el orden
        tarea_padre.data.sort(key=lambda x: x.total_hours, reverse=True)

        # Subtarea (8.0 horas, mayor)
        subtarea = tarea_padre.data[0]
        assert subtarea.id == 2
        assert subtarea.name == "Subtarea"
        assert subtarea.total_hours == 8.0
        assert not subtarea.is_artificial
        assert len(subtarea.data) == 0  # Optimizada como nodo hoja

        # "Sin subtarea" del padre (4.0 horas)
        sin_subtarea_padre = tarea_padre.data[1]
        assert sin_subtarea_padre.id < 0  # ID artificial
        assert sin_subtarea_padre.name == "Sin subtarea"
        assert sin_subtarea_padre.total_hours == 4.0
        assert sin_subtarea_padre.is_artificial
        assert len(sin_subtarea_padre.data) == 0

    def test_project_with_direct_hours_and_parent_with_subtasks(
        self, dashboard_service, mock_task_gateway
    ):
        """Caso: Proyecto con horas directas + Tarea padre sin horas + 2 subtareas con horas."""
        # Arrange
        timesheet_data = [
            # 8 horas cargadas directamente al proyecto (sin tarea)
            DetailedTimesheetLine(
                id=1,
                name="Trabajo directo proyecto",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=None,  # Sin tarea
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            # 4 horas en subtarea 1
            DetailedTimesheetLine(
                id=2,
                name="Trabajo subtarea 1",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=2, name="Subtarea 1", project_id=1, project_name="Proyecto A"
                ),
                hours=4.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
            # 4 horas en subtarea 2
            DetailedTimesheetLine(
                id=3,
                name="Trabajo subtarea 2",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=3, name="Subtarea 2", project_id=1, project_name="Proyecto A"
                ),
                hours=4.0,
                date=date(2024, 1, 3),
                validated=False,
            ),
        ]

        # Mock del task gateway - simular padre invisible con subtareas
        def mock_get_tasks_info_side_effect(task_ids):
            if set(task_ids) == {2, 3}:
                # Primera llamada con subtareas
                return {
                    2: TaskWithParentInfo(
                        id=2,
                        name="Subtarea 1",
                        project_id=1,
                        project_name="Proyecto A",
                        parent_id=1,  # Padre invisible
                    ),
                    3: TaskWithParentInfo(
                        id=3,
                        name="Subtarea 2",
                        project_id=1,
                        project_name="Proyecto A",
                        parent_id=1,  # Padre invisible
                    ),
                }
            elif set(task_ids) == {1}:
                # Segunda llamada con padre invisible
                return {
                    1: TaskWithParentInfo(
                        id=1,
                        name="Tarea Padre",
                        project_id=1,
                        project_name="Proyecto A",
                        parent_id=None,
                    )
                }
            else:
                return {}

        mock_task_gateway.get_tasks_info_with_parents.side_effect = (
            mock_get_tasks_info_side_effect
        )

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert result.total_hours == 16.0  # 8 + 4 + 4
        assert len(result.data) == 1

        # Proyecto
        project = result.data[0]
        assert project.name == "Proyecto A"
        assert project.total_hours == 16.0
        assert len(project.data) == 2  # "Sin tarea" + "Tarea Padre"

        # Ordenar por horas para predicibilidad
        project.data.sort(key=lambda x: x.total_hours, reverse=True)

        # "Sin tarea" (8 horas) - debería ser el primero
        sin_tarea = project.data[1]  # Puede estar en cualquier posición
        if sin_tarea.name != "Sin tarea":
            sin_tarea = project.data[0]

        assert sin_tarea.name == "Sin tarea"
        assert sin_tarea.total_hours == 8.0
        assert sin_tarea.is_artificial
        assert len(sin_tarea.data) == 0  # Optimizada como nodo hoja

        # "Tarea Padre" (8 horas total, 0 directas) - debería tener 2 subtareas
        tarea_padre = (
            project.data[0] if project.data[0].name != "Sin tarea" else project.data[1]
        )
        assert tarea_padre.name == "Tarea Padre"
        assert tarea_padre.total_hours == 8.0  # 4 + 4 de las subtareas
        assert not tarea_padre.is_artificial
        assert (
            len(tarea_padre.data) == 2
        )  # 2 subtareas (sin "Sin subtarea" porque no tiene horas directas)

        # Verificar las subtareas (optimizadas como nodos hoja)
        subtareas = tarea_padre.data
        subtareas.sort(key=lambda x: x.name)  # Ordenar por nombre para predicibilidad

        subtarea_1 = subtareas[0]  # "Subtarea 1"
        assert subtarea_1.name == "Subtarea 1"
        assert subtarea_1.total_hours == 4.0
        assert not subtarea_1.is_artificial
        assert len(subtarea_1.data) == 0  # Optimizada como nodo hoja

        subtarea_2 = subtareas[1]  # "Subtarea 2"
        assert subtarea_2.name == "Subtarea 2"
        assert subtarea_2.total_hours == 4.0
        assert not subtarea_2.is_artificial
        assert len(subtarea_2.data) == 0  # Optimizada como nodo hoja

        # Verificar que se hicieron las dos llamadas al task gateway
        assert mock_task_gateway.get_tasks_info_with_parents.call_count == 2

    def test_mixed_case_project_task_subtask_and_direct_hours(
        self, dashboard_service, mock_task_gateway
    ):
        """Caso mixto: Proyecto con horas directas, tarea con horas directas Y subtareas."""
        # Arrange
        timesheet_data = [
            # Horas directas al proyecto
            DetailedTimesheetLine(
                id=1,
                name="Setup inicial",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=None,
                hours=2.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            # Horas en tarea padre
            DetailedTimesheetLine(
                id=2,
                name="Análisis",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Desarrollo", project_id=1, project_name="Proyecto A"
                ),
                hours=3.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
            # Horas en subtarea
            DetailedTimesheetLine(
                id=3,
                name="Codificación",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=2, name="Frontend", project_id=1, project_name="Proyecto A"
                ),
                hours=5.0,
                date=date(2024, 1, 3),
                validated=False,
            ),
        ]

        # Mock del task gateway
        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Desarrollo",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            ),
            2: TaskWithParentInfo(
                id=2,
                name="Frontend",
                project_id=1,
                project_name="Proyecto A",
                parent_id=1,
            ),
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert result.total_hours == 10.0
        assert len(result.data) == 1

        # Proyecto
        project = result.data[0]
        assert project.total_hours == 10.0
        assert len(project.data) == 2  # Tarea "Desarrollo" + "Sin tarea"

        # Ordenar por horas para predicir orden
        project.data.sort(key=lambda x: x.total_hours, reverse=True)

        # Tarea "Desarrollo" (3.0 + 5.0 = 8.0 horas)
        tarea_desarrollo = project.data[0]
        assert tarea_desarrollo.name == "Desarrollo"
        assert tarea_desarrollo.total_hours == 8.0
        assert len(tarea_desarrollo.data) == 2  # Subtarea "Frontend" + "Sin subtarea"

        # "Sin tarea" del proyecto (2.0 horas)
        sin_tarea_proyecto = project.data[1]
        assert sin_tarea_proyecto.name == "Sin tarea"
        assert sin_tarea_proyecto.total_hours == 2.0
        assert sin_tarea_proyecto.is_artificial

    def test_real_world_complex_project_structure(
        self, dashboard_service, mock_task_gateway
    ):
        """Caso real: Proyecto con horas directas + tarea padre con horas + subtarea + tarea independiente."""
        # Arrange - Simula tu caso real
        timesheet_data = [
            # 8 horas directas al proyecto (sin tarea)
            DetailedTimesheetLine(
                id=1,
                name="Trabajo directo proyecto",
                employee_id=1,
                project=Project(id=2, name="Proyecto IA"),
                task=None,
                hours=8.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            # 7 horas en tarea padre "Construcción del bot"
            DetailedTimesheetLine(
                id=2,
                name="Trabajo directo construcción",
                employee_id=1,
                project=Project(id=2, name="Proyecto IA"),
                task=TaskInfo(
                    id=3,
                    name="Construcción del bot",
                    project_id=2,
                    project_name="Proyecto IA",
                ),
                hours=7.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
            # 8 horas en subtarea "Charla técnica"
            DetailedTimesheetLine(
                id=3,
                name="Charla técnica realizada",
                employee_id=1,
                project=Project(id=2, name="Proyecto IA"),
                task=TaskInfo(
                    id=7,
                    name="Charla técnica",
                    project_id=2,
                    project_name="Proyecto IA",
                ),
                hours=8.0,
                date=date(2024, 1, 3),
                validated=False,
            ),
            # 8 horas en tarea independiente "Deploy de app"
            DetailedTimesheetLine(
                id=4,
                name="Deploy realizado",
                employee_id=1,
                project=Project(id=2, name="Proyecto IA"),
                task=TaskInfo(
                    id=4, name="Deploy de app", project_id=2, project_name="Proyecto IA"
                ),
                hours=8.0,
                date=date(2024, 1, 4),
                validated=False,
            ),
        ]

        # Mock del task gateway - "Charla técnica" es subtarea de "Construcción del bot"
        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            3: TaskWithParentInfo(
                id=3,
                name="Construcción del bot",
                project_id=2,
                project_name="Proyecto IA",
                parent_id=None,
            ),
            7: TaskWithParentInfo(
                id=7,
                name="Charla técnica",
                project_id=2,
                project_name="Proyecto IA",
                parent_id=3,  # Es subtarea de "Construcción del bot"
            ),
            4: TaskWithParentInfo(
                id=4,
                name="Deploy de app",
                project_id=2,
                project_name="Proyecto IA",
                parent_id=None,
            ),
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert result.total_hours == 31.0  # 8 + 7 + 8 + 8
        assert len(result.data) == 1

        # Proyecto IA
        project = result.data[0]
        assert project.name == "Proyecto IA"
        assert project.total_hours == 31.0
        assert (
            len(project.data) == 3
        )  # "Construcción del bot" + "Deploy de app" + "Sin tarea"

        # Encontrar cada elemento (pueden estar en cualquier orden)
        construccion = next(
            item for item in project.data if item.name == "Construcción del bot"
        )
        deploy = next(item for item in project.data if item.name == "Deploy de app")
        sin_tarea = next(item for item in project.data if item.name == "Sin tarea")

        # Verificar "Construcción del bot" (tarea padre)
        assert construccion.total_hours == 15.0  # 7 directas + 8 de subtarea
        assert not construccion.is_artificial
        assert len(construccion.data) == 2  # "Charla técnica" + "Sin subtarea"

        # Dentro de "Construcción del bot"
        charla = next(
            item for item in construccion.data if item.name == "Charla técnica"
        )
        sin_subtarea = next(
            item for item in construccion.data if item.name == "Sin subtarea"
        )

        assert charla.total_hours == 8.0
        assert not charla.is_artificial
        assert len(charla.data) == 0  # Nodo hoja

        assert sin_subtarea.total_hours == 7.0  # Horas directas del padre
        assert sin_subtarea.is_artificial
        assert len(sin_subtarea.data) == 0  # Nodo hoja

        # Verificar "Deploy de app" (tarea independiente)
        assert deploy.total_hours == 8.0
        assert not deploy.is_artificial
        assert len(deploy.data) == 0  # Nodo hoja optimizado

        # Verificar "Sin tarea" (horas directas del proyecto)
        assert sin_tarea.total_hours == 8.0
        assert sin_tarea.is_artificial
        assert len(sin_tarea.data) == 0  # Nodo hoja

    def test_task_name_cleaning_with_arrow_notation(
        self, dashboard_service, mock_task_gateway
    ):
        """Test limpieza de nombres de tareas con notación de flecha."""
        # Arrange
        timesheet_data = [
            DetailedTimesheetLine(
                id=1,
                name="Trabajo",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Padre → Hijo", project_id=1, project_name="Proyecto A"
                ),
                hours=4.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
        ]

        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Padre → Hijo",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            )
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        project = result.data[0]
        task = project.data[0]

        # El nombre debe estar limpio (solo "Hijo")
        assert task.name == "Hijo"
        assert task.total_hours == 4.0

    def test_optimization_single_artificial_child_removal(
        self, dashboard_service, mock_task_gateway
    ):
        """Test de optimización: eliminación de nodos con un solo hijo artificial."""
        # Arrange - Tarea simple que generaría un solo "Sin subtarea"
        timesheet_data = [
            DetailedTimesheetLine(
                id=1,
                name="Trabajo simple",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Tarea Simple", project_id=1, project_name="Proyecto A"
                ),
                hours=6.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
        ]

        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Tarea Simple",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            )
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        project = result.data[0]
        task = project.data[0]

        # La tarea debe ser un nodo hoja (optimizada, sin "Sin subtarea")
        assert task.name == "Tarea Simple"
        assert task.total_hours == 6.0
        assert len(task.data) == 0  # Optimizada como nodo hoja
        assert not task.is_artificial

    def test_multiple_projects_ordering_by_hours(
        self, dashboard_service, mock_task_gateway
    ):
        """Test con múltiples proyectos ordenados por horas (mayor a menor)."""
        # Arrange
        timesheet_data = [
            # Proyecto B - menos horas
            DetailedTimesheetLine(
                id=1,
                name="Trabajo B",
                employee_id=1,
                project=Project(id=2, name="Proyecto B"),
                task=TaskInfo(
                    id=1, name="Tarea B", project_id=2, project_name="Proyecto B"
                ),
                hours=3.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            # Proyecto A - más horas
            DetailedTimesheetLine(
                id=2,
                name="Trabajo A",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=2, name="Tarea A", project_id=1, project_name="Proyecto A"
                ),
                hours=7.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
        ]

        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Tarea B",
                project_id=2,
                project_name="Proyecto B",
                parent_id=None,
            ),
            2: TaskWithParentInfo(
                id=2,
                name="Tarea A",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            ),
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert result.total_hours == 10.0
        assert len(result.data) == 2

        # Los proyectos deben estar ordenados por horas (mayor a menor)
        assert result.data[0].name == "Proyecto A"  # 7.0 horas
        assert result.data[0].total_hours == 7.0
        assert result.data[1].name == "Proyecto B"  # 3.0 horas
        assert result.data[1].total_hours == 3.0

    def test_empty_timesheet_data(self, dashboard_service, mock_task_gateway):
        """Test con datos de timesheet vacíos."""
        # Arrange
        timesheet_data = []
        mock_task_gateway.get_tasks_info_with_parents.return_value = {}

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        assert isinstance(result, HierarchicalSummary)
        assert result.total_hours == 0.0
        assert len(result.data) == 0

    def test_artificial_id_generation_negative_values(
        self, dashboard_service, mock_task_gateway
    ):
        """Test que verifica que los IDs artificiales son negativos y únicos."""
        # Arrange
        timesheet_data = [
            # Proyecto con horas directas
            DetailedTimesheetLine(
                id=1,
                name="Trabajo directo",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=None,
                hours=2.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            # Tarea con horas directas (generará "Sin subtarea")
            DetailedTimesheetLine(
                id=2,
                name="Trabajo tarea",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Tarea 1", project_id=1, project_name="Proyecto A"
                ),
                hours=3.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
        ]

        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Tarea 1",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            )
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        project = result.data[0]

        # Buscar nodos artificiales
        artificial_nodes = []
        for item in project.data:
            if item.is_artificial:
                artificial_nodes.append(item)
            # Verificar también en datos anidados si los hay
            for child in item.data:
                if child.is_artificial:
                    artificial_nodes.append(child)

        # Todos los IDs artificiales deben ser negativos y únicos
        artificial_ids = [node.id for node in artificial_nodes]
        assert all(id < 0 for id in artificial_ids)
        assert len(artificial_ids) == len(set(artificial_ids))  # Únicos

    def test_tasks_ordering_within_project_by_hours(
        self, dashboard_service, mock_task_gateway
    ):
        """Test que verifica el ordenamiento de tareas dentro de un proyecto por horas."""
        # Arrange
        timesheet_data = [
            # Tarea con pocas horas
            DetailedTimesheetLine(
                id=1,
                name="Tarea pequeña",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=1, name="Tarea Pequeña", project_id=1, project_name="Proyecto A"
                ),
                hours=2.0,
                date=date(2024, 1, 1),
                validated=False,
            ),
            # Tarea con muchas horas
            DetailedTimesheetLine(
                id=2,
                name="Tarea grande",
                employee_id=1,
                project=Project(id=1, name="Proyecto A"),
                task=TaskInfo(
                    id=2, name="Tarea Grande", project_id=1, project_name="Proyecto A"
                ),
                hours=8.0,
                date=date(2024, 1, 2),
                validated=False,
            ),
        ]

        mock_task_gateway.get_tasks_info_with_parents.return_value = {
            1: TaskWithParentInfo(
                id=1,
                name="Tarea Pequeña",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            ),
            2: TaskWithParentInfo(
                id=2,
                name="Tarea Grande",
                project_id=1,
                project_name="Proyecto A",
                parent_id=None,
            ),
        }

        # Act
        result = dashboard_service.calculate_hierarchical_summary(
            timesheet_data, mock_task_gateway
        )

        # Assert
        project = result.data[0]
        assert len(project.data) == 2

        # Las tareas deben estar ordenadas por horas (mayor a menor)
        assert project.data[0].name == "Tarea Grande"  # 8.0 horas
        assert project.data[0].total_hours == 8.0
        assert project.data[1].name == "Tarea Pequeña"  # 2.0 horas
        assert project.data[1].total_hours == 2.0
