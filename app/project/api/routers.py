from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.project.api.schemas import ProjectResponse
from app.project.application.use_cases.obtener_proyectos import ObtenerProyectosUseCase
from app.project.domain.gateway import ProjectGateway
from app.project.infra.external.odd_project_gateway import OdooProjectGateway
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.task.application.Exeptions import ProjectsNotFound_userId
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
    user: int,
    gateway: ProjectGateway = Depends(get_project_gateway),
    task_gateway: OdooTaskGateway = Depends(get_task_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene los proyectos. Si se proporciona un user_id, devuelve solo los proyectos
    asociados a ese usuario.

    Args:
        user: ID del usuario del cual obtener los proyectos (opcional)
        gateway: Gateway de proyectos (inyectado)
        task_gateway: Gateway de tareas (inyectado)

    Returns:
        List[ProjectResponse]: Lista de proyectos
    """
    try:
        use_case = ObtenerProyectosUseCase(gateway, task_gateway)
        projects = use_case.execute(user)
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
            )
            for project in projects
        ]
    except ProjectsNotFound_userId as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor al obtener los proyectos")
