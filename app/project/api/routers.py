from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.project.api.schemas import ProjectResponse
from app.project.application.use_cases.obtener_proyectos import ObtenerProyectosUseCase
from app.project.application.use_cases.obtener_proyectos_asignados import (
    ObtenerProyectosAsignadosUseCase,
)
from app.project.domain.gateway import ProjectAssignmentGateway, ProjectGateway
from app.project.infra.external.odd_project_gateway import OdooProjectGateway
from app.project.infra.external.odoo_project_assignment_gateway import (
    OdooProjectAssignmentGateway,
)
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.shared.security.dependencies import get_current_user
from app.shared.security.roles import Roles, user_has_role
from app.users.domain.repositories import EmployeeGateway
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway


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


def get_project_assignment_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
    current_user: dict = Depends(get_current_user),
) -> ProjectAssignmentGateway:
    try:
        return OdooProjectAssignmentGateway(odoo_connection)
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Error al conectar con el gateway de asignaciones a proyecto",
        )


def get_employee_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
    current_user: dict = Depends(get_current_user),
) -> EmployeeGateway:
    try:
        return OdooEmployeeGateway(odoo_connection)
    except Exception:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de empleados"
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
    project_assignment_gateway: ProjectAssignmentGateway = Depends(
        get_project_assignment_gateway
    ),
    employee_gateway: EmployeeGateway = Depends(get_employee_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene los proyectos que el usuario puede usar para cargar horas.

    Un admin (rol approver) ve todos los proyectos activos. Cualquier otro
    usuario ve sólo los proyectos a los que está asignado (``project.assignment``
    vigente) más los que gerencia.

    Args:
        gateway: Gateway de proyectos (inyectado)
        project_assignment_gateway: Gateway de asignaciones a proyecto (inyectado)
        employee_gateway: Gateway de empleados (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        List[ProjectResponse]: Lista de proyectos
    """
    is_admin = user_has_role(current_user.get("roles"), Roles.approver)

    if is_admin:
        projects = ObtenerProyectosUseCase(gateway).execute()
    else:
        employee_id = current_user["user_id"]
        user_id = employee_gateway.get_user_id_by_employee_id(employee_id)
        projects = ObtenerProyectosAsignadosUseCase(
            project_assignment_gateway
        ).execute(employee_id, user_id)

    return [
        ProjectResponse(
            id=project.id,
            name=project.name,
        )
        for project in projects
    ]

