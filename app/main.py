from contextlib import asynccontextmanager
import os
from fastapi import FastAPI

app = FastAPI()

ENV = os.getenv("ENV", "local")  # Por defecto, local

@asynccontextmanager
async def lifespan(app):
    if ENV == "local":
        # En local, creamos las tablas automáticamente. En staging y production lo vamos a manejar con alembic.
        from shared.infra.db.base import Base
        from shared.infra.db.session import engine
        Base.metadata.create_all(bind=engine)
    yield  # acá arranca la app

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Health check"}
