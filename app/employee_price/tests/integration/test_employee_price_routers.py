import pytest
from datetime import date
from fastapi.testclient import TestClient
from fastapi import FastAPI
from sqlmodel import Session
from unittest.mock import Mock, patch

from app.employee_price.api.routers import (
    router,
    get_timesheet_gateway,
    get_employee_gateway,
)
from app.shared.security.dependencies import get_current_user
from app.shared.security.role_enums.dev import Roles
from app.employee_price.infra.db.models import EmployeePriceModel
from app.users.infra.db.models import UserModel
from app.users.domain.models import Employee
from app.shared.infra.db.session import get_db
from app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway import (
    OdooTimesheetLineGateway,
)


def _real_timesheet_gateway_override():
    """Override que devuelve un `OdooTimesheetLineGateway` real con una
    conexión Odoo fake. Lo usan los tests de `GET /employees-price/` que
    parchean `OdooTimesheetLineGateway.get_team_users` a nivel de clase con
    `@patch`: necesitamos la clase real para que el patch tenga efecto."""
    return OdooTimesheetLineGateway(Mock())

# Crear una aplicación de FastAPI para pruebas
app = FastAPI()
app.include_router(router)


def _build_team_gateway_override(team_member_ids: list[int]):
    """
    Construye un override de `get_timesheet_gateway` que devuelve un mock cuyo
    `get_team_users` reporta los IDs indicados como miembros del equipo.
    Lo usamos para satisfacer el scope check introducido por VT-02 sin tocar
    cada test individualmente.
    """

    def override():
        gateway = Mock()
        gateway.get_team_users.return_value = [
            {
                "id": member_id,
                "name": f"User {member_id}",
                "work_email": f"u{member_id}@example.com",
            }
            for member_id in team_member_ids
        ]
        return gateway

    return override


def _build_employee_gateway_override(requester_employee: Employee | None):
    """
    Construye un override de `get_employee_gateway` que devuelve un mock cuyo
    `get_by_id` reporta el Employee indicado (o None) para el solicitante.
    """

    def override():
        gateway = Mock()
        gateway.get_by_id.return_value = requester_employee
        return gateway

    return override


@pytest.fixture
def client_admin(local_db_session):
    """Fixture que proporciona un TestClient con usuario admin.

    Por defecto, el admin (user_id=1) tiene como equipo a los sample_users
    (IDs 1, 2 y 3) para que los tests existentes sigan funcionando luego de
    introducir el scope check de VT-02 en `GET /history/{employee_id}` y
    `POST /`. Tests específicos de IDOR pueden usar `client_admin_empty_team`.
    """

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],
        }

    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_timesheet_gateway] = _build_team_gateway_override(
        [1, 2, 3]
    )
    app.dependency_overrides[get_employee_gateway] = _build_employee_gateway_override(
        Employee(id=1, email="admin@example.com", full_name="Admin User")
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_admin_empty_team(local_db_session):
    """Fixture de admin cuyo equipo en Odoo está vacío.

    Se usa para verificar el cierre del IDOR de VT-02: aunque el usuario tenga
    rol `approver`, si el `employee_id` consultado no está en su equipo, la
    respuesta debe ser 403.
    """

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],
        }

    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_timesheet_gateway] = _build_team_gateway_override([])
    app.dependency_overrides[get_employee_gateway] = _build_employee_gateway_override(
        Employee(id=1, email="admin@example.com", full_name="Admin User")
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def client_admin_no_employee(local_db_session):
    """Fixture de admin sin empleado asociado en Odoo.

    Garantiza que `ensure_employee_in_team` devuelve 403 cuando el solicitante
    no tiene un `Employee` en Odoo, evitando cualquier bypass por usuarios
    huérfanos.
    """

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],
        }

    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_timesheet_gateway] = _build_team_gateway_override(
        [2, 3]
    )
    app.dependency_overrides[get_employee_gateway] = _build_employee_gateway_override(
        None
    )
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
            "roles": [1],
        }

    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_current_user] = mock_regular_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_timesheet_gateway] = _build_team_gateway_override([])
    app.dependency_overrides[get_employee_gateway] = _build_employee_gateway_override(
        Employee(id=2, email="user@example.com", full_name="Regular User")
    )
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_users(local_db_session: Session):
    """Fixture que crea usuarios de prueba en la base de datos."""
    users = [
        UserModel(
            id=1,
            email="admin@example.com",
            full_name="Admin User",
            hashed_password="hashed_password_admin",
        ),
        UserModel(
            id=2,
            email="user@example.com",
            full_name="Regular User",
            hashed_password="hashed_password_user",
        ),
        UserModel(
            id=3,
            email="employee@example.com",
            full_name="Employee User",
            hashed_password="hashed_password_employee",
        ),
    ]

    for user in users:
        local_db_session.add(user)
    local_db_session.commit()

    for user in users:
        local_db_session.refresh(user)

    yield users

    # Cleanup
    for user in users:
        local_db_session.delete(user)
    local_db_session.commit()


@pytest.fixture
def sample_employee_prices(local_db_session: Session, sample_users):
    """Fixture que crea registros de precios de empleados de prueba."""
    prices = [
        EmployeePriceModel(
            user_id=2,
            date_from=date(2024, 1, 1),
            date_to=None,
            cost_per_hour=50.0,
        ),
        EmployeePriceModel(
            user_id=2,
            date_from=date(2023, 6, 1),
            date_to=date(2024, 1, 1),
            cost_per_hour=45.0,
        ),
        EmployeePriceModel(
            user_id=3,
            date_from=date(2024, 1, 1),
            date_to=None,
            cost_per_hour=60.0,
        ),
    ]

    for price in prices:
        local_db_session.add(price)
    local_db_session.commit()

    for price in prices:
        local_db_session.refresh(price)

    yield prices

    # Cleanup
    for price in prices:
        local_db_session.delete(price)
    local_db_session.commit()


# ========== Tests para POST /employees-price/ (crear precio de empleado) ==========


@pytest.mark.integration
def test_create_employee_price_success(client_admin, sample_users):
    """Test de integración: creación exitosa de precio de empleado."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 55.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "Registro de precio de empleado creado exitosamente" in data["message"]
    assert "employee_price" in data

    employee_price = data["employee_price"]
    assert employee_price["user_id"] == 2
    assert employee_price["cost_per_hour"] == 55.0
    assert employee_price["date_from"] == "2024-06-01"
    assert employee_price["date_to"] is None
    assert employee_price["id"] is not None
    assert "email" in employee_price
    assert "full_name" in employee_price


@pytest.mark.integration
def test_create_employee_price_with_cost_per_hour_none(client_admin, sample_users):
    """Test de integración: creación con cost_per_hour=None."""
    # Arrange
    request_data = {
        "employee_id": 3,
        "date_from": "2024-06-01",
        "cost_per_hour": None,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    employee_price = data["employee_price"]
    assert employee_price["cost_per_hour"] is None


@pytest.mark.integration
def test_create_employee_price_closes_previous_open_record(
    client_admin, sample_users, sample_employee_prices, local_db_session
):
    """Test de integración: crear nuevo precio cierra el registro previo abierto."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 75.0,
    }

    # Refrescar la sesión para obtener el estado actual
    local_db_session.expire_all()

    # Contar registros abiertos antes
    open_records_count_before = (
        local_db_session.query(EmployeePriceModel)
        .filter(
            EmployeePriceModel.user_id == 2,
            EmployeePriceModel.date_to == None,  # noqa: E711
        )
        .count()
    )
    assert open_records_count_before >= 1

    # Contar total de registros antes
    total_records_before = (
        local_db_session.query(EmployeePriceModel)
        .filter(EmployeePriceModel.user_id == 2)
        .count()
    )

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200

    # Refrescar la sesión después del cambio
    local_db_session.expire_all()

    # Verificar que se agregó un nuevo registro
    total_records_after = (
        local_db_session.query(EmployeePriceModel)
        .filter(EmployeePriceModel.user_id == 2)
        .count()
    )
    assert total_records_after == total_records_before + 1

    # Verificar que hay un registro abierto con el nuevo costo
    new_record = (
        local_db_session.query(EmployeePriceModel)
        .filter(
            EmployeePriceModel.user_id == 2,
            EmployeePriceModel.cost_per_hour == 75.0,
            EmployeePriceModel.date_to == None,  # noqa: E711
        )
        .first()
    )
    assert new_record is not None, "Debe existir un registro abierto con el nuevo costo"


@pytest.mark.integration
def test_create_employee_price_employee_not_found(local_db_session):
    """Error 404 cuando el empleado está en el equipo pero no existe en la BD local."""
    # Arrange: empleado 99999 forma parte del equipo del admin (Odoo) pero no
    # existe en la BD local; el scope check pasa y caemos al 404 de la BD.
    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],
        }

    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_timesheet_gateway] = _build_team_gateway_override(
        [99999]
    )
    app.dependency_overrides[get_employee_gateway] = _build_employee_gateway_override(
        Employee(id=1, email="admin@example.com", full_name="Admin User")
    )

    try:
        with TestClient(app) as client:
            request_data = {
                "employee_id": 99999,
                "date_from": "2024-06-01",
                "cost_per_hour": 55.0,
            }

            # Act
            response = client.post("/employees-price/", json=request_data)

            # Assert
            assert response.status_code == 404
            error_detail = response.json()["detail"]
            assert "El empleado 99999 no se ha registrado en el sistema" in error_detail
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_create_employee_price_negative_cost_per_hour(client_admin, sample_users):
    """Test de integración: error con cost_per_hour negativo."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": -10.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    # Pydantic valida en el schema antes de llegar al use case, retorna 422
    assert response.status_code == 422


@pytest.mark.integration
def test_create_employee_price_zero_cost_per_hour(client_admin, sample_users):
    """Test de integración: error con cost_per_hour igual a 0."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 0.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    # Pydantic valida en el schema antes de llegar al use case, retorna 422
    assert response.status_code == 422


@pytest.mark.integration
def test_create_employee_price_invalid_date_format(client_admin, sample_users):
    """Test de integración: error con formato de fecha inválido."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "invalid-date",
        "cost_per_hour": 55.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
def test_create_employee_price_missing_required_fields(client_admin, sample_users):
    """Test de integración: error cuando faltan campos requeridos."""
    # Arrange
    request_data = {
        "employee_id": 2,
        # Falta date_from
        "cost_per_hour": 55.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 422  # Validation error


@pytest.mark.integration
def test_create_employee_price_response_structure(client_admin, sample_users):
    """Test de integración: verifica estructura completa de la respuesta."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 55.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()

    # Verificar estructura de nivel superior
    assert "success" in data
    assert "message" in data
    assert "employee_price" in data

    # Verificar estructura de employee_price
    employee_price = data["employee_price"]
    required_fields = {
        "id",
        "user_id",
        "email",
        "full_name",
        "date_from",
        "cost_per_hour",
        "date_to",
    }
    assert set(employee_price.keys()) == required_fields


# ========== Tests para GET /employees-price/history/{employee_id} ==========


@pytest.mark.integration
def test_get_employee_price_history_success(
    client_admin, sample_users, sample_employee_prices
):
    """Test de integración: obtención exitosa del historial de precios."""
    # Arrange
    employee_id = 2

    # Act
    response = client_admin.get(f"/employees-price/history/{employee_id}")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # Debe tener al menos los 2 registros creados

    # Verificar estructura del primer registro
    if data:
        price_record = data[0]
        assert "id" in price_record
        assert "user_id" in price_record
        assert "date_from" in price_record
        assert "date_to" in price_record
        assert "cost_per_hour" in price_record
        assert price_record["user_id"] == employee_id


@pytest.mark.integration
def test_get_employee_price_history_empty_for_employee_without_prices(
    client_admin, sample_users
):
    """Test de integración: historial vacío para empleado sin registros."""
    # Arrange
    employee_id = 1  # Usuario sin registros de precio

    # Act
    response = client_admin.get(f"/employees-price/history/{employee_id}")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.integration
def test_get_employee_price_history_employee_not_found(local_db_session):
    """Error 404 cuando el empleado está en el equipo pero no existe en la BD local."""
    # Arrange: empleado 99999 forma parte del equipo del admin pero no tiene
    # registro en la BD local; el scope check pasa y caemos al 404.
    employee_id = 99999

    async def mock_admin_user():
        return {
            "user_id": 1,
            "user_email": "admin@example.com",
            "user_name": "Admin User",
            "roles": [Roles.approver],
        }

    def override_get_db():
        yield local_db_session

    app.dependency_overrides[get_current_user] = mock_admin_user
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_timesheet_gateway] = _build_team_gateway_override(
        [employee_id]
    )
    app.dependency_overrides[get_employee_gateway] = _build_employee_gateway_override(
        Employee(id=1, email="admin@example.com", full_name="Admin User")
    )

    try:
        with TestClient(app) as client:
            # Act
            response = client.get(f"/employees-price/history/{employee_id}")

            # Assert
            assert response.status_code == 404
            error_detail = response.json()["detail"]
            assert (
                f"Empleado con employee_id {employee_id} no encontrado" in error_detail
            )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.integration
def test_get_employee_price_history_with_multiple_records(
    client_admin, sample_users, sample_employee_prices, local_db_session
):
    """Test de integración: historial con múltiples registros ordenados."""
    # Arrange
    employee_id = 2

    # Agregar un tercer registro
    new_price = EmployeePriceModel(
        user_id=2,
        date_from=date(2023, 1, 1),
        date_to=date(2023, 6, 1),
        cost_per_hour=40.0,
    )
    local_db_session.add(new_price)
    local_db_session.commit()

    # Act
    response = client_admin.get(f"/employees-price/history/{employee_id}")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert len(data) >= 3

    # Verificar que todos los registros son del empleado correcto
    for record in data:
        assert record["user_id"] == employee_id

    # Cleanup
    local_db_session.delete(new_price)
    local_db_session.commit()


@pytest.mark.integration
def test_get_employee_price_history_response_format(
    client_admin, sample_users, sample_employee_prices
):
    """Test de integración: verifica formato de respuesta consistente."""
    # Arrange
    employee_id = 2

    # Act
    response = client_admin.get(f"/employees-price/history/{employee_id}")

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert isinstance(data, list)

    # Verificar estructura de cada item
    for item in data:
        assert isinstance(item, dict)
        assert "id" in item
        assert "user_id" in item
        assert "date_from" in item
        assert "cost_per_hour" in item or item["cost_per_hour"] is None


@pytest.mark.integration
def test_get_employee_price_history_with_open_and_closed_records(
    client_admin, sample_users, sample_employee_prices
):
    """Test de integración: historial con registros abiertos y cerrados."""
    # Arrange
    employee_id = 2

    # Act
    response = client_admin.get(f"/employees-price/history/{employee_id}")

    # Assert
    assert response.status_code == 200

    data = response.json()

    # Debe haber al menos un registro abierto (date_to = None)
    open_records = [r for r in data if r["date_to"] is None]
    assert len(open_records) >= 1

    # Debe haber al menos un registro cerrado (date_to != None)
    closed_records = [r for r in data if r["date_to"] is not None]
    assert len(closed_records) >= 1


# ========== Tests para GET /employees-price/ (listar precios del equipo) ==========
#
# El endpoint `GET /employees-price/` NO recibe `get_employee_gateway` por
# Depends (lo instancia inline), por eso los tests siguen usando `@patch` para
# `OdooEmployeeGateway.get_by_id`. Pero sí recibe `get_timesheet_gateway`, que
# la fixture `client_admin` ahora overridea por defecto para satisfacer el
# scope check de VT-02. Antes de testear `GET /`, eliminamos ese override
# puntual para que el `@patch` sobre `OdooTimesheetLineGateway.get_team_users`
# vuelva a tener efecto.


@pytest.mark.integration
@patch("app.employee_price.api.routers.get_odoo_connection")
@patch(
    "app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway.OdooTimesheetLineGateway.get_team_users"
)
@patch("app.users.infra.external.odoo_gateway.OdooEmployeeGateway.get_by_id")
def test_list_team_employee_prices_success(
    mock_get_by_id,
    mock_get_team_users,
    mock_odoo_connection,
    client_admin,
    sample_users,
    sample_employee_prices,
):
    """Test de integración: listar precios del equipo exitosamente."""
    # Arrange
    app.dependency_overrides[get_timesheet_gateway] = _real_timesheet_gateway_override

    mock_get_by_id.return_value = Employee(
        id=1, email="admin@example.com", full_name="Admin User"
    )

    mock_get_team_users.return_value = [
        {"id": 2, "name": "Regular User", "work_email": "user@example.com"},
        {"id": 3, "name": "Employee User", "work_email": "employee@example.com"},
    ]

    mock_odoo_connection.return_value = Mock()

    # Act
    response = client_admin.get("/employees-price/")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2

    # Verificar estructura de cada item
    for item in data:
        assert "employee_id" in item
        assert "name" in item
        assert "email" in item
        assert "cost_per_hour" in item
        assert "date_from" in item
        assert "date_to" in item


@pytest.mark.integration
@patch("app.employee_price.api.routers.get_odoo_connection")
@patch(
    "app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway.OdooTimesheetLineGateway.get_team_users"
)
@patch("app.users.infra.external.odoo_gateway.OdooEmployeeGateway.get_by_id")
def test_list_team_employee_prices_empty_team(
    mock_get_by_id, mock_get_team_users, mock_odoo_connection, client_admin
):
    """Test de integración: lista vacía cuando no hay equipo."""
    # Arrange
    app.dependency_overrides[get_timesheet_gateway] = _real_timesheet_gateway_override

    mock_get_by_id.return_value = Employee(
        id=1, email="admin@example.com", full_name="Admin User"
    )

    mock_get_team_users.return_value = []
    mock_odoo_connection.return_value = Mock()

    # Act
    response = client_admin.get("/employees-price/")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


@pytest.mark.integration
@patch("app.employee_price.api.routers.get_odoo_connection")
@patch("app.users.infra.external.odoo_gateway.OdooEmployeeGateway.get_by_id")
def test_list_team_employee_prices_user_without_employee(
    mock_get_by_id, mock_odoo_connection, client_admin
):
    """Test de integración: error cuando el usuario no tiene empleado asociado."""
    # Arrange
    app.dependency_overrides[get_timesheet_gateway] = _real_timesheet_gateway_override
    mock_get_by_id.return_value = None  # Usuario sin empleado
    mock_odoo_connection.return_value = Mock()

    # Act
    response = client_admin.get("/employees-price/")

    # Assert
    assert response.status_code == 400
    error_detail = response.json()["detail"]
    assert "El usuario no tiene un empleado asociado" in error_detail


@pytest.mark.integration
@patch("app.employee_price.api.routers.get_odoo_connection")
@patch(
    "app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway.OdooTimesheetLineGateway.get_team_users"
)
@patch("app.users.infra.external.odoo_gateway.OdooEmployeeGateway.get_by_id")
def test_list_team_employee_prices_with_members_without_prices(
    mock_get_by_id,
    mock_get_team_users,
    mock_odoo_connection,
    client_admin,
    sample_users,
):
    """Test de integración: miembros del equipo sin registros de precio."""
    # Arrange
    app.dependency_overrides[get_timesheet_gateway] = _real_timesheet_gateway_override

    mock_get_by_id.return_value = Employee(
        id=1, email="admin@example.com", full_name="Admin User"
    )

    # Usuario 1 no tiene registros de precio
    mock_get_team_users.return_value = [
        {"id": 1, "name": "Admin User", "work_email": "admin@example.com"},
    ]

    mock_odoo_connection.return_value = Mock()

    # Act
    response = client_admin.get("/employees-price/")

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    assert data[0]["employee_id"] == 1
    assert data[0]["cost_per_hour"] is None
    assert data[0]["date_from"] is None


@pytest.mark.integration
@patch("app.employee_price.api.routers.get_odoo_connection")
@patch(
    "app.timesheet_line.infra.external.odoo.odoo_timesheet_gateway.OdooTimesheetLineGateway.get_team_users"
)
@patch("app.users.infra.external.odoo_gateway.OdooEmployeeGateway.get_by_id")
def test_list_team_employee_prices_response_structure(
    mock_get_by_id,
    mock_get_team_users,
    mock_odoo_connection,
    client_admin,
    sample_users,
    sample_employee_prices,
):
    """Test de integración: verifica estructura de respuesta."""
    # Arrange
    app.dependency_overrides[get_timesheet_gateway] = _real_timesheet_gateway_override

    mock_get_by_id.return_value = Employee(
        id=1, email="admin@example.com", full_name="Admin User"
    )

    mock_get_team_users.return_value = [
        {"id": 2, "name": "Regular User", "work_email": "user@example.com"},
    ]

    mock_odoo_connection.return_value = Mock()

    # Act
    response = client_admin.get("/employees-price/")

    # Assert
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    data = response.json()
    assert isinstance(data, list)

    if data:
        item = data[0]
        required_fields = {
            "employee_id",
            "name",
            "email",
            "cost_per_hour",
            "date_from",
            "date_to",
        }
        assert set(item.keys()) == required_fields


# ========== Tests adicionales de casos edge ==========


@pytest.mark.integration
def test_create_employee_price_with_future_date(client_admin, sample_users):
    """Test de integración: crear precio con fecha futura."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2025-01-01",
        "cost_per_hour": 75.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["employee_price"]["date_from"] == "2025-01-01"


@pytest.mark.integration
def test_create_employee_price_with_past_date(client_admin, sample_users):
    """Test de integración: crear precio con fecha pasada."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2020-01-01",
        "cost_per_hour": 35.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["employee_price"]["date_from"] == "2020-01-01"


@pytest.mark.integration
def test_create_employee_price_with_high_cost(client_admin, sample_users):
    """Test de integración: crear precio con costo muy alto."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 1000.0,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["employee_price"]["cost_per_hour"] == 1000.0


@pytest.mark.integration
def test_create_employee_price_with_fractional_cost(client_admin, sample_users):
    """Test de integración: crear precio con costo decimal."""
    # Arrange
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 45.75,
    }

    # Act
    response = client_admin.post("/employees-price/", json=request_data)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["employee_price"]["cost_per_hour"] == 45.75


@pytest.mark.integration
def test_get_employee_price_history_consistent_results(
    client_admin, sample_users, sample_employee_prices
):
    """Test de integración: resultados consistentes en múltiples llamadas."""
    # Arrange
    employee_id = 2

    # Act
    response1 = client_admin.get(f"/employees-price/history/{employee_id}")
    response2 = client_admin.get(f"/employees-price/history/{employee_id}")

    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200

    data1 = response1.json()
    data2 = response2.json()

    assert len(data1) == len(data2)

    # Verificar que los IDs son los mismos
    ids1 = [record["id"] for record in data1]
    ids2 = [record["id"] for record in data2]
    assert ids1 == ids2


@pytest.mark.integration
def test_employee_price_endpoints_content_type(client_admin, sample_users):
    """Test de integración: verifica content-type de las respuestas."""
    # Arrange
    create_request = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 55.0,
    }

    # Act & Assert - POST
    response_create = client_admin.post("/employees-price/", json=create_request)
    assert response_create.headers["content-type"] == "application/json"

    # Act & Assert - GET history
    response_history = client_admin.get("/employees-price/history/2")
    assert response_history.headers["content-type"] == "application/json"


# ==========================================================================
# Tests de regresión VT-02 (IDOR / Broken Object-Level Authorization)
# ==========================================================================
# Estos tests bloquean la regresión de la vulnerabilidad de fuga de datos
# salariales reportada en el pentest 2026-04 (GEO-1403). Antes del fix,
# cualquier usuario con rol `approver` podía:
#   - Leer el historial de costo por hora de CUALQUIER empleado.
#   - Sobrescribir el costo por hora de CUALQUIER empleado.
# Después del fix, el solicitante debe ser miembro del equipo del target
# (jerarquía Odoo) o el propio empleado.


@pytest.mark.integration
def test_get_employee_price_history_blocks_idor_when_target_not_in_team(
    client_admin_empty_team, sample_users, sample_employee_prices
):
    """VT-02: 403 cuando el approver consulta el historial de un empleado
    que NO pertenece a su equipo en Odoo."""
    target_employee_id = 2  # existe en la BD, pero no en el equipo del admin

    response = client_admin_empty_team.get(
        f"/employees-price/history/{target_employee_id}"
    )

    assert response.status_code == 403
    assert "permisos" in response.json()["detail"].lower()


@pytest.mark.integration
def test_create_employee_price_blocks_idor_when_target_not_in_team(
    client_admin_empty_team, sample_users
):
    """VT-02: 403 cuando el approver intenta crear/sobrescribir el costo de un
    empleado que NO pertenece a su equipo en Odoo."""
    request_data = {
        "employee_id": 2,  # existe en la BD, pero no en el equipo del admin
        "date_from": "2024-06-01",
        "cost_per_hour": 9999.0,
    }

    response = client_admin_empty_team.post("/employees-price/", json=request_data)

    assert response.status_code == 403
    assert "permisos" in response.json()["detail"].lower()


@pytest.mark.integration
def test_get_employee_price_history_blocks_when_requester_has_no_employee(
    client_admin_no_employee, sample_users, sample_employee_prices
):
    """VT-02: 403 cuando el solicitante no tiene Employee asociado en Odoo,
    aunque tenga rol approver y el target sí exista."""
    response = client_admin_no_employee.get("/employees-price/history/2")

    assert response.status_code == 403
    assert "empleado asociado" in response.json()["detail"].lower()


@pytest.mark.integration
def test_create_employee_price_blocks_when_requester_has_no_employee(
    client_admin_no_employee, sample_users
):
    """VT-02: 403 al crear precio cuando el solicitante no tiene Employee
    asociado en Odoo."""
    request_data = {
        "employee_id": 2,
        "date_from": "2024-06-01",
        "cost_per_hour": 55.0,
    }

    response = client_admin_no_employee.post("/employees-price/", json=request_data)

    assert response.status_code == 403
    assert "empleado asociado" in response.json()["detail"].lower()


@pytest.mark.integration
def test_get_employee_price_history_allows_self_access(
    client_admin_empty_team, sample_users, sample_employee_prices, local_db_session
):
    """VT-02: el solicitante siempre puede ver SU PROPIO historial, incluso si
    el `get_team_users` devuelve un equipo vacío (self-access)."""
    # El admin tiene Employee.id == 1 según la fixture; le creo un registro de
    # precio propio para validar el camino feliz.
    own_price = EmployeePriceModel(
        user_id=1,
        date_from=date(2024, 1, 1),
        date_to=None,
        cost_per_hour=80.0,
    )
    local_db_session.add(own_price)
    local_db_session.commit()

    try:
        response = client_admin_empty_team.get("/employees-price/history/1")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(record["user_id"] == 1 for record in data)
    finally:
        local_db_session.delete(own_price)
        local_db_session.commit()


@pytest.mark.integration
def test_create_employee_price_allows_self_access(
    client_admin_empty_team, sample_users
):
    """VT-02: el solicitante puede crear/actualizar su propio costo aunque su
    equipo en Odoo esté vacío (self-access permitido)."""
    request_data = {
        "employee_id": 1,  # el propio admin
        "date_from": "2024-06-01",
        "cost_per_hour": 90.0,
    }

    response = client_admin_empty_team.post("/employees-price/", json=request_data)

    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.integration
def test_get_employee_price_history_does_not_leak_existence_via_404(
    client_admin_empty_team, sample_users, sample_employee_prices
):
    """VT-02: ante un target fuera de scope, la respuesta debe ser 403 sin
    importar si el employee_id existe (2) o no (99999). Esto evita que un
    atacante use el código de respuesta para enumerar IDs válidos."""
    response_existing = client_admin_empty_team.get("/employees-price/history/2")
    response_unknown = client_admin_empty_team.get("/employees-price/history/99999")

    assert response_existing.status_code == 403
    assert response_unknown.status_code == 403
