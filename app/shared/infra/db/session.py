# src/shared/db/session.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# En staging vamos a tener la url de la base de datos de staging
# En production vamos a tener la url de la base de datos de production
# En local  creamos una base de datos en sqlite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
