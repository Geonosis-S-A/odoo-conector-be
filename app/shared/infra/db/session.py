from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.shared.infra.db.config import (
    settings,
)


# Crear el motor de la base de datos
def create_engine_with_url(database_url: str):
    connect_args = (
        {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    )
    return create_engine(database_url, connect_args=connect_args)


# Crear una sesión de base de datos
def create_session_local(engine):
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Motor y sesión para la base de datos de desarrollo/producción
engine = create_engine_with_url(settings.DATABASE_URL)
SessionLocal = create_session_local(engine)


# Dependencia para obtener la sesión de la base de datos
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
