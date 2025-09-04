from fastapi import APIRouter, Depends, HTTPException
from typing import List

from app.shared.security.dependencies import get_current_user
from app.task.api.schemas import TaskResponse
from app.task.application.Exeptions import (
    ProjectNotFound,
    TasksNotFound_projectId,
    TasksNotFound_userId,
)
from app.task.application.use_cases.obtener_tareas import ObtenerTareasUseCase
from app.task.domain.gateway import TaskGateway
from app.task.infra.external.odoo_task_gateway import OdooTaskGateway
from app.shared.infra.external.odoo.odoo_client import (
    get_odoo_connection_dependency,
    OdooConnection,
)
from app.users.infra.external.odoo_gateway import OdooEmployeeGateway
from app.auth.application.use_cases.exceptions.exceptions import UserNotFound

router = APIRouter(tags=["tasks"])


def get_task_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> TaskGateway:
    try:
        return OdooTaskGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Error al conectar con el gateway de tareas"
        )


def get_employee_gateway(
    odoo_connection: OdooConnection = Depends(get_odoo_connection_dependency),
) -> OdooEmployeeGateway:
    try:
        return OdooEmployeeGateway(odoo_connection)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[TaskResponse])
async def get_tasks(
    project_id: int,
    gateway: TaskGateway = Depends(get_task_gateway),
    odoo_task_gateway: OdooTaskGateway = Depends(get_task_gateway),
    odoo_employee_gateway: OdooEmployeeGateway = Depends(get_employee_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene las tareas asociadas a un proyecto específico.

    Args:
        project_id: ID del proyecto del cual obtener las tareas
        gateway: Gateway de tareas (inyectado)

    Returns:
        List[TaskResponse]: Lista de tareas del proyecto
    """
    try:
        use_case = ObtenerTareasUseCase(
            gateway, odoo_task_gateway, odoo_employee_gateway
        )
        tasks = use_case.execute(project_id)

        return [
            TaskResponse(
                id=task.id,
                name=task.name,
                project_id=task.project_id,
                project_name=task.project_name,
                state=task.state,
            )
            for task in tasks
        ]
    except ProjectNotFound as e:
        raise HTTPException(status_code=404, detail=e.message)
    except TasksNotFound_projectId as e:
        raise HTTPException(status_code=404, detail=e.message)
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/user", response_model=List[TaskResponse])
async def get_tasks_by_user(
    user_id: int,
    gateway: TaskGateway = Depends(get_task_gateway),
    odoo_task_gateway: OdooTaskGateway = Depends(get_task_gateway),
    odoo_employee_gateway: OdooEmployeeGateway = Depends(get_employee_gateway),
    current_user: dict = Depends(get_current_user),
):
    """
    Obtiene las tareas asignadas al usuario autenticado.

    Args:
        gateway: Gateway de tareas (inyectado)
        current_user: Usuario autenticado (inyectado)

    Returns:
        List[TaskResponse]: Lista de tareas asignadas al usuario
    """
    try:
        use_case = ObtenerTareasUseCase(
            gateway, odoo_task_gateway, odoo_employee_gateway
        )
        tasks = use_case.execute_by_user(user_id)
        return [
            TaskResponse(
                id=task.id,
                name=task.name,
                project_id=task.project_id,
                project_name=task.project_name,
                state=task.state,
            )
            for task in tasks
        ]
    except TasksNotFound_userId as e:
        raise HTTPException(status_code=404, detail=e.message)
    except UserNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
