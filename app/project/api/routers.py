from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.project.api.schemas import ProjectResponse
from app.project.application.use_cases.obtener_proyectos import ObtenerProyectosUseCase
from app.project.domain.gateway import ProjectGateway
from app.project.infra.external.odd_project_gateway import OdooProjectGateway
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.shared.security.dependencies import get_current_user


router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
    current_user: dict = Depends(get_current_user),
) -> ProjectGateway:
    try:
        return OdooProjectGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de proyectos"
        )


def get_task_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
    current_user: dict = Depends(get_current_user),
) -> OdooTaskGateway:
    try:
        return OdooTaskGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de tareas"
        )


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    gateway: ProjectGateway = Depends(get_project_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene los proyectos que el usuario puede usar para cargar horas.

    Todos los proyectos activos, para cualquier usuario autenticado. No se
    filtra por ``project.assignment``: esa asignación está lejos de cubrir a
    todos los empleados que efectivamente trabajan en un proyecto, así que
    filtrar por ella ocultaba proyectos reales al cargar horas. Quién puede
    VER/VALIDAR las horas de otro empleado se sigue resolviendo aparte, vía
    ``TeamAccessService`` (jerarquía ∪ proyectos gerenciados).

    Args:
        gateway: Gateway de proyectos (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        List[ProjectResponse]: Lista de proyectos
    """
    projects = ObtenerProyectosUseCase(gateway).execute()

    return [
        ProjectResponse(
            id=project.id,
            name=project.name,
        )
        for project in projects
    ]

