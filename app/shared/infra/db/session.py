from sqlalchemy import create_engine
from sqlmodel import Session
from app.shared.infra.db.config import (
    settings,
)


# Crear el motor de la base de datos
def create_engine_with_url(database_url: str):
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(database_url, connect_args=connect_args)


# Motor para la base de datos de desarrollo/producción
engine = create_engine_with_url(settings.DATABASE_URL)


# Dependencia para obtener la sesión de la base de datos usando SQLModel
def get_db():
    with Session(engine) as session:
        yield session
