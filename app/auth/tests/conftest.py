import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool


@pytest.fixture(name="test_session")
def test_session_fixture():
    """Crear una sesión de base de datos para tests"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    # Crear todas las tablas
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session 