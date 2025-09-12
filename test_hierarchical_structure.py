#!/usr/bin/env python3
"""
Script de prueba para verificar la nueva estructura jerárquica del dashboard.
Este script simula datos de timesheet y verifica que la lógica funcione correctamente.
"""

from datetime import date
from app.dashboard.infra.dashboard_service import OdooDashboardDataService
from app.timesheet_line.domain.models import DetailedTimesheetLine
from app.project.domain.models import Project
from app.task.domain.models import TaskInfo, TaskWithParentInfo
from app.task.domain.gateway import TaskGateway
from typing import List, Dict


class MockTaskGateway(TaskGateway):
    """Mock del TaskGateway para pruebas."""

    def __init__(self):
        # Simular estructura de tareas con padres e hijos
        self.task_info = {
            1: TaskWithParentInfo(
                id=1,
                name="Tarea Padre 1",
                project_id=1,
                project_name="Proyecto 1",
                parent_id=None,
            ),
            2: TaskWithParentInfo(
                id=2,
                name="Subtarea 1",
                project_id=1,
                project_name="Proyecto 1",
                parent_id=1,
            ),
            3: TaskWithParentInfo(
                id=3,
                name="Subtarea 2",
                project_id=1,
                project_name="Proyecto 1",
                parent_id=1,
            ),
            4: TaskWithParentInfo(
                id=4,
                name="Tarea Sin Subtareas",
                project_id=1,
                project_name="Proyecto 1",
                parent_id=None,
            ),
        }

    def all(self, project_id: int):
        return None

    def get_project_by_id(self, project_id: int):
        return None

    def get_tasks_info_with_parents(
        self, task_ids: List[int]
    ) -> Dict[int, TaskWithParentInfo]:
        return {
            task_id: info
            for task_id, info in self.task_info.items()
            if task_id in task_ids
        }


def create_test_data() -> List[DetailedTimesheetLine]:
    """Crea datos de prueba simulando diferentes escenarios."""

    project1 = Project(id=1, name="Proyecto 1")
    project2 = Project(id=92, name="Proyecto 2")

    # Tareas del proyecto 1
    task_padre = TaskInfo(
        id=1, name="Tarea Padre 1", project_id=1, project_name="Proyecto 1"
    )
    subtarea1 = TaskInfo(
        id=2, name="Subtarea 1", project_id=1, project_name="Proyecto 1"
    )
    subtarea2 = TaskInfo(
        id=3, name="Subtarea 2", project_id=1, project_name="Proyecto 1"
    )
    tarea_sin_subtareas = TaskInfo(
        id=4, name="Tarea Sin Subtareas", project_id=1, project_name="Proyecto 1"
    )

    test_date = date(2024, 1, 15)

    return [
        # Horas en subtareas (deben agregarse a la tarea padre)
        DetailedTimesheetLine(
            id=1,
            name="Entrada 1",
            employee_id=1,
            project=project1,
            task=subtarea1,
            hours=5.0,
            date=test_date,
            validated=True,
        ),
        DetailedTimesheetLine(
            id=2,
            name="Entrada 2",
            employee_id=1,
            project=project1,
            task=subtarea2,
            hours=1.0,
            date=test_date,
            validated=True,
        ),
        # Horas directas en tarea padre (debe crear "Sin subtarea")
        DetailedTimesheetLine(
            id=3,
            name="Entrada 3",
            employee_id=1,
            project=project1,
            task=task_padre,
            hours=1.0,
            date=test_date,
            validated=True,
        ),
        # Horas en tarea sin subtareas (debe crear "Sin subtarea")
        DetailedTimesheetLine(
            id=4,
            name="Entrada 4",
            employee_id=1,
            project=project1,
            task=tarea_sin_subtareas,
            hours=2.0,
            date=test_date,
            validated=True,
        ),
        # Horas directas al proyecto sin tarea (debe crear "Sin tarea")
        DetailedTimesheetLine(
            id=5,
            name="Entrada 5",
            employee_id=1,
            project=project2,
            task=None,
            hours=2.0,
            date=test_date,
            validated=True,
        ),
    ]


def main():
    """Función principal para ejecutar las pruebas."""
    print("🧪 Iniciando pruebas de la estructura jerárquica...")

    # Crear mocks y datos de prueba
    mock_task_gateway = MockTaskGateway()
    dashboard_service = OdooDashboardDataService(None, None, None, None)
    test_data = create_test_data()

    print(f"📊 Procesando {len(test_data)} líneas de timesheet...")

    # Ejecutar el cálculo de la estructura jerárquica
    hierarchical_summary = dashboard_service.calculate_hierarchical_summary(
        test_data, mock_task_gateway
    )

    print(f"\n✅ Estructura jerárquica calculada:")
    print(f"   Total de horas: {hierarchical_summary.total_hours}")
    print(f"   Total de entradas: {hierarchical_summary.total_entries}")
    print(f"   Número de proyectos: {len(hierarchical_summary.data)}")

    # Imprimir estructura detallada
    for project_item in hierarchical_summary.data:
        print(f"\n🗂️  Proyecto: {project_item.name} (ID: {project_item.id})")
        print(
            f"   Horas totales: {project_item.total_hours}, Entradas: {project_item.total_entries}"
        )

        for task_item in project_item.data:
            artificial_flag = " [ARTIFICIAL]" if task_item.is_artificial else ""
            print(
                f"   📋 Tarea: {task_item.name} (ID: {task_item.id}){artificial_flag}"
            )
            print(
                f"      Horas: {task_item.total_hours}, Entradas: {task_item.total_entries}"
            )

            for subtask_item in task_item.data:
                artificial_flag = " [ARTIFICIAL]" if subtask_item.is_artificial else ""
                print(
                    f"      🔸 Subtarea: {subtask_item.name} (ID: {subtask_item.id}){artificial_flag}"
                )
                print(
                    f"         Horas: {subtask_item.total_hours}, Entradas: {subtask_item.total_entries}"
                )

    print(f"\n🎉 Pruebas completadas exitosamente!")


if __name__ == "__main__":
    main()
