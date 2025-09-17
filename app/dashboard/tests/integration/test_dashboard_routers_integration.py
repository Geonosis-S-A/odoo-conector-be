import pytest
from datetime import date
from fastapi.testclient import TestClient
from fastapi import FastAPI
from app.dashboard.api.routers import router
from app.shared.infra.external.odoo.odoo_client import get_odoo_connection
from app.shared.security.dependencies import get_current_user
from app.shared.security.role_enums.dev import Roles

# Crear una aplicación de FastAPI para pruebas
app = FastAPI()
app.include_router(router)


@pytest.fixture(autouse=True)
def setup_odoo_connection():
    """Fixture que configura la conexión real a Odoo."""
    odoo_client = get_odoo_connection()
    yield {"odoo_client": odoo_client}
    # No hay limpieza específica aquí porque usamos servicios de solo lectura


@pytest.fixture
def client_admin(local_db_session):
    """Fixture que proporciona un TestClient con usuario admin."""

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],  # Rol de admin
        }

    app.dependency_overrides[get_current_user] = mock_admin_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_regular(local_db_session):
    """Fixture que proporciona un TestClient con usuario regular."""

    async def mock_regular_user():
        return {
            "user_id": 2,
            "user_email": "user@example.com",
            "user_name": "Regular User",
            "roles": [1],  # Rol de empleado regular
        }

    app.dependency_overrides[get_current_user] = mock_regular_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.integration
def test_get_dashboard_summary_success_admin_user(client_admin):
    """Test de integración: dashboard summary exitoso con usuario admin y datos reales."""
    # Arrange
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert "meta" in data
    assert "summary" in data
    assert "totals" in data

    # Verificar estructura de meta
    assert "users_count" in data["meta"]
    assert isinstance(data["meta"]["users_count"], int)
    assert data["meta"]["users_count"] >= 0

    # Verificar estructura de summary
    summary = data["summary"]
    assert "hours_selected_period" in summary
    assert "entries_selected_period" in summary
    assert "daily_average_hours" in summary

    # Verificar estructura de KPIs
    for kpi_name in [
        "hours_selected_period",
        "entries_selected_period",
        "daily_average_hours",
    ]:
        kpi = summary[kpi_name]
        assert "total" in kpi
        assert "average_per_user" in kpi
        assert "unit" in kpi
        assert isinstance(kpi["total"], (int, float))
        assert isinstance(kpi["average_per_user"], (int, float))
        assert isinstance(kpi["unit"], (str, type(None)))

    # Verificar estructura de totals
    totals = data["totals"]
    assert "by_project" in totals
    assert "by_task" in totals
    assert "by_employee" in totals

    # hierarchical_summary está en el nivel superior, puede ser None si no hay datos
    assert "hierarchical_summary" in data
    # hierarchical_summary puede ser None, dict o no existir según los datos
    assert data["hierarchical_summary"] is None or isinstance(
        data["hierarchical_summary"], dict
    )

    # Verificar que las listas son válidas
    assert isinstance(totals["by_project"], list)
    assert isinstance(totals["by_task"], list)
    assert isinstance(totals["by_employee"], list)

    # Si hay datos, verificar estructura
    if totals["by_project"]:
        project = totals["by_project"][0]
        assert "project_id" in project
        assert "project_name" in project
        assert "hours" in project
        assert isinstance(project["project_id"], int)
        assert isinstance(project["project_name"], str)
        assert isinstance(project["hours"], (int, float))

    if totals["by_task"]:
        task = totals["by_task"][0]
        assert "task_id" in task
        assert "task_name" in task
        assert "hours" in task
        assert "project_id" in task
        assert isinstance(task["task_id"], int)
        assert isinstance(task["task_name"], str)
        assert isinstance(task["hours"], (int, float))
        assert isinstance(task["project_id"], int)

    if totals["by_employee"]:
        employee = totals["by_employee"][0]
        assert "user_id" in employee
        assert "employee_name" in employee
        assert "hours" in employee
        assert isinstance(employee["user_id"], int)
        assert isinstance(employee["employee_name"], str)
        assert isinstance(employee["hours"], (int, float))

    # Verificar estructura jerárquica si existe
    if data["hierarchical_summary"]:
        hierarchical = data["hierarchical_summary"]
        assert "total_hours" in hierarchical
        assert "data" in hierarchical
        assert isinstance(hierarchical["total_hours"], (int, float))
        assert isinstance(hierarchical["data"], list)


@pytest.mark.integration
def test_get_dashboard_summary_forbidden_regular_user(client_regular):
    """Test de integración: dashboard summary con usuario sin permisos."""
    # Arrange
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_regular.get(
        "/dashboard/summary",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 403
    error_detail = response.json()["detail"]
    assert "No tienes permisos para ver el dashboard" in error_detail


@pytest.mark.integration
def test_get_dashboard_summary_invalid_date_range(client_admin):
    """Test de integración: dashboard summary con rango de fechas inválido."""
    # Arrange
    test_date_from = date(2024, 1, 31)  # Fecha posterior
    test_date_to = date(2024, 1, 1)  # Fecha anterior

    # Act
    response = client_admin.get(
        "/dashboard/summary",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert "La fecha de inicio no puede ser posterior a la fecha de fin" in error_detail


@pytest.mark.integration
def test_get_dashboard_summary_empty_date_range(client_admin):
    """Test de integración: dashboard summary con rango de fechas sin datos."""
    # Arrange - Usar un rango de fechas muy antiguo donde no hay datos
    test_date_from = date(1990, 1, 1)
    test_date_to = date(1990, 1, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    # Debe devolver estructura válida pero con totales en 0
    assert data["meta"]["users_count"] >= 0
    assert data["summary"]["hours_selected_period"]["total"] >= 0
    assert data["summary"]["entries_selected_period"]["total"] >= 0
    assert data["summary"]["daily_average_hours"]["total"] >= 0

    # Las listas pueden estar vacías
    assert isinstance(data["totals"]["by_project"], list)
    assert isinstance(data["totals"]["by_task"], list)
    assert isinstance(data["totals"]["by_employee"], list)


@pytest.mark.integration
def test_get_dashboard_summary_consistent_results(client_admin):
    """Test de integración: dashboard summary retorna resultados consistentes."""
    # Arrange
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)
    params = {
        "date_from": test_date_from.isoformat(),
        "date_to": test_date_to.isoformat(),
    }

    # Act - Hacer múltiples llamadas
    response1 = client_admin.get("/dashboard/summary", params=params)
    response2 = client_admin.get("/dashboard/summary", params=params)

    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Los resultados deben ser consistentes
    assert data1["meta"]["users_count"] == data2["meta"]["users_count"]
    assert (
        data1["summary"]["hours_selected_period"]["total"]
        == data2["summary"]["hours_selected_period"]["total"]
    )
    assert len(data1["totals"]["by_project"]) == len(data2["totals"]["by_project"])
    assert len(data1["totals"]["by_task"]) == len(data2["totals"]["by_task"])
    assert len(data1["totals"]["by_employee"]) == len(data2["totals"]["by_employee"])


@pytest.mark.integration
def test_get_dashboard_summary_by_employee_success_same_user(client_regular):
    """Test de integración: dashboard by employee exitoso para el mismo usuario."""
    # Arrange
    test_employee_id = 2  # Mismo ID que el usuario autenticado
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_regular.get(
        f"/dashboard/summary/{test_employee_id}",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert "meta" in data
    assert "summary" in data
    assert "totals" in data

    # Verificar estructura específica para empleado individual
    meta = data["meta"]
    assert "users_count" in meta
    assert "worked_days" in meta
    assert isinstance(meta["users_count"], int)
    assert isinstance(meta["worked_days"], int)
    assert meta["users_count"] == 1  # Solo un empleado

    # Verificar estructura de summary
    summary = data["summary"]
    assert "hours_selected_period" in summary
    assert "entries_selected_period" in summary
    assert "daily_average_hours" in summary

    # Verificar estructura de totals
    totals = data["totals"]
    assert "by_project" in totals
    assert "by_task" in totals
    assert "by_employee" in totals

    # hierarchical_summary está en el nivel superior, puede ser None si no hay datos
    assert "hierarchical_summary" in data
    assert data["hierarchical_summary"] is None or isinstance(
        data["hierarchical_summary"], dict
    )

    # Para empleado individual, by_employee debe tener máximo 1 elemento
    assert len(totals["by_employee"]) <= 1
    if totals["by_employee"]:
        employee = totals["by_employee"][0]
        assert employee["user_id"] == test_employee_id


@pytest.mark.integration
def test_get_dashboard_summary_by_employee_success_admin_different_user(client_admin):
    """Test de integración: dashboard by employee con admin consultando otro empleado."""
    # Arrange
    test_employee_id = 1  # ID diferente al usuario autenticado (admin)
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_admin.get(
        f"/dashboard/summary/{test_employee_id}",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert "meta" in data
    assert "summary" in data
    assert "totals" in data

    # Admin puede ver cualquier empleado
    assert data["meta"]["users_count"] == 1


@pytest.mark.integration
def test_get_dashboard_summary_by_employee_forbidden_different_user(client_regular):
    """Test de integración: usuario regular no puede consultar otros empleados."""
    # Arrange
    test_employee_id = 1  # ID diferente al usuario autenticado (2)
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_regular.get(
        f"/dashboard/summary/{test_employee_id}",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 403
    error_detail = response.json()["detail"]
    assert "No tienes permisos para ver esta información" in error_detail


@pytest.mark.integration
def test_get_dashboard_summary_by_employee_invalid_date_range(client_regular):
    """Test de integración: dashboard by employee con rango de fechas inválido."""
    # Arrange
    test_employee_id = 2  # Mismo ID que el usuario
    test_date_from = date(2024, 1, 31)  # Fecha posterior
    test_date_to = date(2024, 1, 1)  # Fecha anterior

    # Act
    response = client_regular.get(
        f"/dashboard/summary/{test_employee_id}",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert "La fecha de inicio no puede ser posterior a la fecha de fin" in error_detail


@pytest.mark.integration
def test_get_dashboard_summary_by_employee_nonexistent_employee(client_admin):
    """Test de integración: dashboard by employee con empleado inexistente."""
    # Arrange
    test_employee_id = 99999  # ID que no existe
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_admin.get(
        f"/dashboard/summary/{test_employee_id}",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    # Puede retornar 404 si el empleado no existe, o 200 con datos vacíos
    # Depende de la implementación del gateway
    assert response.status_code in [200, 404]

    if response.status_code == 404:
        error_detail = response.json()["detail"]
        assert (
            "no existe" in error_detail.lower() or "not found" in error_detail.lower()
        )
    else:
        # Si retorna 200, debe ser con datos vacíos/mínimos
        data = response.json()
        assert data["meta"]["users_count"] == 0 or data["meta"]["users_count"] == 1


@pytest.mark.integration
def test_get_dashboard_summary_by_employee_empty_date_range(client_regular):
    """Test de integración: dashboard by employee con rango sin datos."""
    # Arrange
    test_employee_id = 2  # Mismo ID que el usuario
    test_date_from = date(1990, 1, 1)  # Fechas muy antiguas sin datos
    test_date_to = date(1990, 1, 31)

    # Act
    response = client_regular.get(
        f"/dashboard/summary/{test_employee_id}",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    # Debe devolver estructura válida pero con totales en 0
    assert data["meta"]["users_count"] >= 0
    assert data["meta"]["worked_days"] >= 0
    assert data["summary"]["hours_selected_period"]["total"] >= 0
    assert data["summary"]["entries_selected_period"]["total"] >= 0
    assert data["summary"]["daily_average_hours"]["total"] >= 0


@pytest.mark.integration
def test_get_dashboard_summary_by_employee_consistent_results(client_regular):
    """Test de integración: dashboard by employee retorna resultados consistentes."""
    # Arrange
    test_employee_id = 2
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)
    params = {
        "date_from": test_date_from.isoformat(),
        "date_to": test_date_to.isoformat(),
    }

    # Act - Hacer múltiples llamadas
    response1 = client_regular.get(
        f"/dashboard/summary/{test_employee_id}", params=params
    )
    response2 = client_regular.get(
        f"/dashboard/summary/{test_employee_id}", params=params
    )

    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Los resultados deben ser consistentes
    assert data1["meta"]["users_count"] == data2["meta"]["users_count"]
    assert data1["meta"]["worked_days"] == data2["meta"]["worked_days"]
    assert (
        data1["summary"]["hours_selected_period"]["total"]
        == data2["summary"]["hours_selected_period"]["total"]
    )


@pytest.mark.integration
def test_dashboard_endpoints_response_format(client_admin):
    """Test de integración: verifica formato de respuesta de ambos endpoints."""
    # Arrange
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)
    params = {
        "date_from": test_date_from.isoformat(),
        "date_to": test_date_to.isoformat(),
    }

    # Act
    response_general = client_admin.get("/dashboard/summary", params=params)
    response_employee = client_admin.get("/dashboard/summary/1", params=params)

    # Assert
    assert response_general.status_code == 200
    assert response_employee.status_code == 200

    # Ambos deben retornar JSON válido
    assert response_general.headers["content-type"] == "application/json"
    assert response_employee.headers["content-type"] == "application/json"

    # Verificar que ambos tienen la misma estructura base
    data_general = response_general.json()
    data_employee = response_employee.json()

    # Ambos deben tener las mismas secciones principales
    expected_sections = {"meta", "summary", "totals", "hierarchical_summary"}
    assert set(data_general.keys()) == expected_sections
    assert set(data_employee.keys()) == expected_sections

    # La diferencia principal está en meta (users_count y worked_days)
    assert "users_count" in data_general["meta"]
    assert "users_count" in data_employee["meta"]
    assert "worked_days" in data_employee["meta"]
    # worked_days puede o no estar en el endpoint general, depende de la implementación


@pytest.mark.integration
def test_dashboard_hierarchical_summary_structure(client_admin):
    """Test de integración: verifica estructura de la respuesta jerárquica."""
    # Arrange
    test_date_from = date(2024, 1, 1)
    test_date_to = date(
        2024, 12, 31
    )  # Rango amplio para tener más posibilidades de datos

    # Act
    response = client_admin.get(
        "/dashboard/summary",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    hierarchical_summary = data.get("hierarchical_summary")

    if hierarchical_summary and hierarchical_summary.get("data"):
        # Verificar estructura jerárquica de proyectos
        for project in hierarchical_summary["data"]:
            assert "type" in project
            assert "id" in project
            assert "name" in project
            assert "total_hours" in project
            assert "data" in project
            assert "is_artificial" in project

            assert project["type"] == "project"
            assert isinstance(project["id"], int)
            assert isinstance(project["name"], str)
            assert isinstance(project["total_hours"], (int, float))
            assert isinstance(project["data"], list)
            assert isinstance(project["is_artificial"], bool)

            # Verificar estructura de tareas dentro del proyecto
            for task in project["data"]:
                assert "type" in task
                assert "id" in task
                assert "name" in task
                assert "total_hours" in task
                assert "data" in task
                assert "is_artificial" in task

                assert task["type"] == "task"
                assert isinstance(task["id"], int)
                assert isinstance(task["name"], str)
                assert isinstance(task["total_hours"], (int, float))
                assert isinstance(task["data"], (list, type(None)))
                assert isinstance(task["is_artificial"], bool)

                # Si la tarea tiene subtareas, verificar su estructura
                if task["data"]:
                    for subtask in task["data"]:
                        assert "type" in subtask
                        assert "id" in subtask
                        assert "name" in subtask
                        assert "total_hours" in subtask
                        assert "data" in subtask
                        assert "is_artificial" in subtask

                        assert subtask["type"] == "task"
                        assert isinstance(subtask["id"], int)
                        assert isinstance(subtask["name"], str)
                        assert isinstance(subtask["total_hours"], (int, float))
                        assert isinstance(subtask["is_artificial"], bool)


@pytest.mark.integration
def test_dashboard_business_logic_validation(client_admin):
    """Test de integración: valida la lógica de negocio específica del dashboard."""
    # Arrange
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()

    # Validaciones de coherencia matemática
    summary = data["summary"]

    # Las horas promedio por usuario deben ser coherentes
    total_hours = summary["hours_selected_period"]["total"]
    avg_hours_per_user = summary["hours_selected_period"]["average_per_user"]
    users_count = data["meta"]["users_count"]

    if users_count > 0 and total_hours > 0:
        expected_avg = total_hours / users_count
        # Permitir pequeñas diferencias por redondeo
        assert abs(avg_hours_per_user - expected_avg) < 0.01, (
            f"Promedio calculado {expected_avg} no coincide con el retornado {avg_hours_per_user}"
        )

    # Validar que las horas totales en hierarchical_summary coinciden con los totales
    hierarchical = data.get("hierarchical_summary")
    if hierarchical and hierarchical.get("total_hours") is not None:
        hierarchical_total = hierarchical["total_hours"]
        # Debe coincidir con el total de horas del período
        assert abs(hierarchical_total - total_hours) < 0.01, (
            f"Total jerárquico {hierarchical_total} no coincide con total del período {total_hours}"
        )

    # Validar que las horas por proyecto suman correctamente
    project_totals = data["totals"]["by_project"]
    if project_totals:
        project_hours_sum = sum(project["hours"] for project in project_totals)
        assert abs(project_hours_sum - total_hours) < 0.01, (
            f"Suma de proyectos {project_hours_sum} no coincide con total {total_hours}"
        )

    print("✅ Validación de lógica de negocio exitosa:")
    print(f"   - Total horas: {total_hours}")
    print(f"   - Usuarios: {users_count}")
    print(f"   - Promedio por usuario: {avg_hours_per_user}")
    print(f"   - Proyectos: {len(project_totals)}")
    print(f"   - Tareas: {len(data['totals']['by_task'])}")
    print(f"   - Empleados: {len(data['totals']['by_employee'])}")


@pytest.mark.integration
def test_get_task_detail_success_with_task_id(client_admin):
    """Test de integración: detalle de tarea exitoso con task_id."""
    # Arrange
    test_task_id = 1  # Usar un ID que probablemente exista
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 12, 31)  # Rango amplio para obtener datos

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert "task_id" in data
    assert "project_id" in data
    assert "timesheet_lines" in data
    assert data["task_id"] == test_task_id
    assert isinstance(data["timesheet_lines"], list)

    # Si hay líneas de timesheet, verificar estructura
    if data["timesheet_lines"]:
        timesheet_line = data["timesheet_lines"][0]
        assert "id" in timesheet_line
        assert "name" in timesheet_line
        assert "employee" in timesheet_line
        assert "hours" in timesheet_line
        assert "date" in timesheet_line
        assert "validated" in timesheet_line
        assert "notification" in timesheet_line

        # Verificar estructura del empleado
        employee = timesheet_line["employee"]
        assert "employee_id" in employee
        assert "employee_name" in employee
        assert isinstance(employee["employee_id"], int)
        assert isinstance(employee["employee_name"], str)

        # Verificar tipos de datos
        assert isinstance(timesheet_line["id"], int)
        assert isinstance(timesheet_line["name"], str)
        assert isinstance(timesheet_line["hours"], (int, float))
        assert isinstance(timesheet_line["validated"], bool)


@pytest.mark.integration
def test_get_task_detail_success_with_project_id(client_admin):
    """Test de integración: detalle de proyecto exitoso con project_id."""
    # Arrange
    test_project_id = 1  # Usar un ID que probablemente exista
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 12, 31)  # Rango amplio para obtener datos

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "project_id": test_project_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] is None
    assert data["project_id"] == test_project_id
    assert isinstance(data["timesheet_lines"], list)

    # Si hay líneas de timesheet, verificar que todas pertenecen al proyecto
    for timesheet_line in data["timesheet_lines"]:
        assert "id" in timesheet_line
        assert "name" in timesheet_line
        assert "employee" in timesheet_line
        assert "hours" in timesheet_line
        assert "date" in timesheet_line
        assert "validated" in timesheet_line
        assert "notification" in timesheet_line


@pytest.mark.integration
def test_get_task_detail_forbidden_regular_user(client_regular):
    """Test de integración: usuario regular no puede acceder al detalle."""
    # Arrange
    test_task_id = 1
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_regular.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 403
    error_detail = response.json()["detail"]
    assert "No tienes permisos para ver esta información" in error_detail


@pytest.mark.integration
def test_get_task_detail_missing_both_ids(client_admin):
    """Test de integración: error cuando no se proporciona task_id ni project_id."""
    # Arrange
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert "Debe proporcionar task_id o project_id" in error_detail


@pytest.mark.integration
def test_get_task_detail_invalid_date_range(client_admin):
    """Test de integración: error con rango de fechas inválido."""
    # Arrange
    test_task_id = 1
    test_date_from = date(2024, 1, 31)  # Fecha posterior
    test_date_to = date(2024, 1, 1)  # Fecha anterior

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert "La fecha de inicio no puede ser posterior a la fecha de fin" in error_detail


@pytest.mark.integration
def test_get_task_detail_nonexistent_task(client_admin):
    """Test de integración: detalle con task_id inexistente."""
    # Arrange
    test_task_id = 99999  # ID que probablemente no existe
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    # Puede retornar 200 con lista vacía o 404, dependiendo de la implementación
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert data["task_id"] == test_task_id
        assert len(data["timesheet_lines"]) == 0  # Lista vacía para tarea inexistente


@pytest.mark.integration
def test_get_task_detail_empty_date_range(client_admin):
    """Test de integración: detalle con rango de fechas sin datos."""
    # Arrange
    test_task_id = 1
    test_date_from = date(1990, 1, 1)  # Fechas muy antiguas sin datos
    test_date_to = date(1990, 1, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["task_id"] == test_task_id
    assert len(data["timesheet_lines"]) == 0  # Sin datos en ese rango


@pytest.mark.integration
def test_get_task_detail_response_format(client_admin):
    """Test de integración: verifica formato de respuesta consistente."""
    # Arrange
    test_task_id = 1
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 12, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # Verificar estructura requerida
    required_fields = {"task_id", "project_id", "timesheet_lines"}
    assert set(data.keys()) == required_fields

    # task_id debe coincidir con el solicitado
    assert data["task_id"] == test_task_id

    # timesheet_lines debe ser una lista
    assert isinstance(data["timesheet_lines"], list)


@pytest.mark.integration
def test_get_task_detail_both_task_and_project_params(client_admin):
    """Test de integración: comportamiento cuando se proporcionan ambos IDs."""
    # Arrange
    test_task_id = 1
    test_project_id = 1
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "project_id": test_project_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()
    # Debe priorizar task_id cuando ambos están presentes
    assert data["task_id"] == test_task_id
    # project_id puede ser None o el ID del proyecto de la tarea


@pytest.mark.integration
def test_get_task_detail_with_notifications(client_admin):
    """Test de integración: verifica que las notificaciones se incluyen correctamente."""
    # Arrange
    test_task_id = 1
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 12, 31)  # Rango amplio

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "task_id": test_task_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()

    # Verificar que cada línea de timesheet tiene el campo notification
    for timesheet_line in data["timesheet_lines"]:
        assert "notification" in timesheet_line

        # Si hay notificación, verificar estructura
        if timesheet_line["notification"] is not None:
            notification = timesheet_line["notification"]
            assert "id" in notification
            assert "sender_name" in notification
            assert "sended_at" in notification
            assert isinstance(notification["id"], int)
            assert isinstance(notification["sender_name"], str)
            assert isinstance(notification["sended_at"], str)


@pytest.mark.integration
def test_get_task_detail_consistent_results(client_admin):
    """Test de integración: verifica que los resultados son consistentes."""
    # Arrange
    test_task_id = 1
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 1, 31)
    params = {
        "task_id": test_task_id,
        "date_from": test_date_from.isoformat(),
        "date_to": test_date_to.isoformat(),
    }

    # Act - Hacer múltiples llamadas
    response1 = client_admin.get("/dashboard/summary/detail", params=params)
    response2 = client_admin.get("/dashboard/summary/detail", params=params)

    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    # Los resultados deben ser consistentes
    assert data1["task_id"] == data2["task_id"]
    assert data1["project_id"] == data2["project_id"]
    assert len(data1["timesheet_lines"]) == len(data2["timesheet_lines"])

    # Verificar que los IDs de las líneas son los mismos
    if data1["timesheet_lines"]:
        ids1 = [line["id"] for line in data1["timesheet_lines"]]
        ids2 = [line["id"] for line in data2["timesheet_lines"]]
        assert ids1 == ids2


@pytest.mark.integration
def test_get_task_detail_data_integrity(client_admin):
    """Test de integración: verifica la integridad de los datos."""
    # Arrange
    test_project_id = 1
    test_date_from = date(2024, 1, 1)
    test_date_to = date(2024, 12, 31)

    # Act
    response = client_admin.get(
        "/dashboard/summary/detail",
        params={
            "project_id": test_project_id,
            "date_from": test_date_from.isoformat(),
            "date_to": test_date_to.isoformat(),
        },
    )

    # Assert
    assert response.status_code == 200

    data = response.json()

    # Verificar integridad de datos
    for timesheet_line in data["timesheet_lines"]:
        # Las horas deben ser positivas o cero
        assert timesheet_line["hours"] >= 0

        # La fecha debe estar en el rango solicitado
        line_date = date.fromisoformat(timesheet_line["date"])
        assert test_date_from <= line_date <= test_date_to

        # El empleado debe tener ID y nombre válidos
        employee = timesheet_line["employee"]
        assert employee["employee_id"] > 0
        assert len(employee["employee_name"].strip()) > 0

        # validated debe ser booleano
        assert isinstance(timesheet_line["validated"], bool)

    print("✅ Validación de integridad de datos exitosa:")
    print(f"   - Líneas de timesheet verificadas: {len(data['timesheet_lines'])}")
    print(f"   - Proyecto ID: {data['project_id']}")
    print(f"   - Tarea ID: {data['task_id']}")
