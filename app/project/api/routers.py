from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.project.api.schemas import ProjectResponse
from app.project.application.use_cases.obtener_proyectos import ObtenerProyectosUseCase
from app.project.domain.gateway import ProjectGateway
from app.project.infra.external.odd_project_gateway import OdooProjectGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)


router = APIRouter(prefix="/projects", tags=["projects"])


def get_project_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> ProjectGateway:
    try:
        return OdooProjectGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de proyectos"
        )


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    user: int | None = None,
    gateway: ProjectGateway = Depends(get_project_gateway),
):
    """
    Obtiene los proyectos. Si se proporciona un user_id, devuelve solo los proyectos
    asociados a ese usuario.

    Args:
        user: ID del usuario del cual obtener los proyectos (opcional)
        gateway: Gateway de proyectos (inyectado)

    Returns:
        List[ProjectResponse]: Lista de proyectos
    """
    try:
        use_case = ObtenerProyectosUseCase(gateway)
        projects = use_case.execute(user)
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
            )
            for project in projects
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al obtener los proyectos",
        )
