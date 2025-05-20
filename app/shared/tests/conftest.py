import pytest
from sqlalchemy.orm import sessionmaker
from app.shared.infra.db.session import create_engine_with_url
from app.shared.infra.db.config import settings
from sqlmodel import SQLModel

# Crear el motor de la base de datos de pruebas
test_engine = create_engine_with_url(settings.TEST_DATABASE_URL)

# Crear la sesión de base de datos para los tests
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


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
    Fixture que proporciona una sesión limpia de la base de datos local (de pruebas)
    para cada test. Los cambios se revierten al final del test.
    """
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()  # Revertir cambios al final del test
        session.close()
