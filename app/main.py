from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.timesheet_line.api.routers import router as timesheet_router
from app.users.api.routers import router as users_router
from app.project.api.routers import router as project_router
from app.task.api.routers import router as task_router
from app.auth.api.routes import router as auth_router
from app.email.api.routes import router as email_router
from app.dashboard.api.routers import router as dashboard_router
from app.employee_price.api.routers import router as employee_price_router
from app.accounting.api.routers import router as accounting_router
from agent.api.routers import router as agent_router
from app.saved_prompts.api.routers import router as saved_prompts_router
from app.timesheet_templates.api.routers import router as timesheet_templates_router
import logging


ENV = os.getenv("ENV", "LOCAL")  # Por defecto, local
API_PREFIX = "/api/v1"


# Configuración básica: loguea a consola y a archivo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),  # Consola
    ],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    if ENV == "LOCAL":
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


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error inesperado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error inesperado. Intenta más tarde."},
    )


# Configuración de CORS
# Configuración de CORS según el entorno
if ENV == "LOCAL":
    allowed_origins = [
        "http://localhost:8080",
    ]
elif ENV == "STAGING":
    allowed_origins = [
        "https://conecta-timesheet-staging.soportegeonosis.com.ar",
    ]
elif ENV == "PROD":
    allowed_origins = [
        "https://geo-timesheet.soportegeonosis.com.ar",
    ]
else:
    allowed_origins = [
        "http://localhost:8080",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
app.include_router(task_router, prefix=API_PREFIX + "/tasks")
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(email_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(employee_price_router, prefix=API_PREFIX)
app.include_router(accounting_router, prefix=API_PREFIX)
app.include_router(agent_router, prefix=API_PREFIX)
app.include_router(saved_prompts_router, prefix=API_PREFIX)
app.include_router(timesheet_templates_router, prefix=API_PREFIX)


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
