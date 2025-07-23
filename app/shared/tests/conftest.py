import pytest
from sqlmodel import SQLModel, Session
from app.shared.infra.db.session import create_engine_with_url, get_db
from app.shared.infra.db.config import settings
from fastapi.testclient import TestClient
from app.shared.security.dependencies import get_current_user

# Crear el motor de la base de datos de pruebas
test_engine = create_engine_with_url(settings.TEST_DATABASE_URL)


@pytest.fixture(scope="module", autouse=True)
def setup_test_database():
    """
    Fixture que crea las tablas en la base de datos de pruebas antes de los tests
    y las elimina después de que todos los tests hayan terminado.
    """
    SQLModel.metadata.create_all(bind=test_engine)
    yield
    SQLModel.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def local_db_session():
    """
    Fixture que proporciona una sesión limpia de SQLModel para cada test.
    Los cambios se revierten al final del test.
    """
    with Session(test_engine) as session:
        try:
            yield session
        finally:
            session.rollback()  # Revertir cambios al final del test


@pytest.fixture(scope="function")
def override_get_db(local_db_session):
    def _override():
        yield local_db_session

    return _override


@pytest.fixture(scope="session")
def override_get_current_user():
    async def _override():
        return {
            "user_id": 1,
            "user_email": "test@example.com",
            "user_name": "Test User",
            "roles": [1],  # Cambio: usar enteros en lugar de strings
        }

    return _override


@pytest.fixture(scope="function")
def test_client(override_get_current_user, override_get_db):
    """
    Fixture que proporciona un TestClient con el override de autenticación centralizado.
    """
    from app.main import (
        app,
    )  # Ajusta el import según la ubicación real de tu app FastAPI

    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
