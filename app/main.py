from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.timesheet_line.api.routers import router as timesheet_router
from app.users.api.routers import router as users_router
from app.project.api.routers import router as project_router

ENV = os.getenv("ENV", "local")  # Por defecto, local
API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(app):
    if ENV == "local":
        # En local, creamos las tablas automáticamente. En staging y production lo vamos a manejar con alembic.
        from sqlmodel import SQLModel
        from app.shared.infra.db.session import engine

        SQLModel.metadata.create_all(bind=engine)
    yield  # acá arranca la app


app = FastAPI(
    title="Odoo Connector API",
    description="API para conectar con Odoo",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs"
    if ENV != "production"
    else None,  # Deshabilitamos Swagger en producción
    redoc_url="/redoc"
    if ENV != "production"
    else None,  # Deshabilitamos ReDoc en producción
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"]
    if ENV == "local"
    else [],  # En producción, especificar los orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Manejadores de errores globales
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


# Incluimos los routers
app.include_router(timesheet_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(project_router, prefix=API_PREFIX)


@app.get("/")
async def root():
    return {
        "message": "Health check",
        "status": "ok",
        "environment": ENV,
        "version": "1.0.0",
    }


@app.get("/health")
async def health_check():
    """
    Endpoint para verificar el estado de la API.
    Útil para monitoreo y balanceadores de carga.
    """
    return {"status": "healthy", "environment": ENV, "version": "1.0.0"}
