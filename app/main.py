from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

ENV = os.getenv("ENV", "local")  # Por defecto, local

@asynccontextmanager
async def lifespan(app):
    if ENV == "local":
        # En local, creamos las tablas automáticamente. En staging y production lo vamos a manejar con alembic.
        from shared.infra.db.base import Base
        from shared.infra.db.session import engine
        Base.metadata.create_all(bind=engine)
    yield  # acá arranca la app

app = FastAPI(
    title="Odoo Connector API",
    description="API para conectar con Odoo",
    version="1.0.0",
    lifespan=lifespan
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Todo: En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Todo: en producción agregar algun limitador de cantidad de requests por IP.

@app.get("/")
async def root():
    return {
        "message": "Health check",
        "status": "ok",
        "environment": ENV
    }
