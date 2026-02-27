from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.timesheet_templates.api.schemas import (
    CreateTimesheetTemplateRequest,
    TimesheetTemplateResponse,
)
from app.timesheet_templates.application.use_cases.create_template import (
    CreateTimesheetTemplateUseCase,
)
from app.timesheet_templates.application.use_cases.list_templates import (
    ListTimesheetTemplatesUseCase,
)
from app.timesheet_templates.application.use_cases.delete_template import (
    DeleteTimesheetTemplateUseCase,
)
from app.timesheet_templates.domain.repositories import TimesheetTemplateRepository
from app.timesheet_templates.infra.db.repositories import (
    SQLModelTimesheetTemplateRepository,
)
from app.shared.infra.db.session import get_db
from app.shared.security.dependencies import get_current_user
from app.auth.infra.auth_service import JWTPayload


router = APIRouter(prefix="/timesheet-templates", tags=["timesheet-templates"])


def get_template_repository(
    db: Session = Depends(get_db),
) -> TimesheetTemplateRepository:
    """Dependency para obtener el repositorio de templates."""
    return SQLModelTimesheetTemplateRepository(db)


@router.post("/", response_model=TimesheetTemplateResponse, status_code=201)
async def create_template(
    request: CreateTimesheetTemplateRequest,
    repository: TimesheetTemplateRepository = Depends(get_template_repository),
    current_user: JWTPayload = Depends(get_current_user),
):
    """Crea un nuevo template de carga para el usuario autenticado."""
    try:
        user_id = current_user["user_id"]
        use_case = CreateTimesheetTemplateUseCase(repository)
        template = use_case.execute(
            user_id=user_id,
            name=request.name,
            project_id=request.project_id,
            task_id=request.task_id,
        )

        if template.id is None:
            raise HTTPException(status_code=500, detail="Error: template guardado sin ID")

        return TimesheetTemplateResponse(
            id=template.id,
            user_id=template.user_id,
            name=template.name,
            project_id=template.project_id,
            task_id=template.task_id,
            created_at=template.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al guardar el template: {str(e)}"
        )


@router.get("/", response_model=List[TimesheetTemplateResponse])
async def list_templates(
    repository: TimesheetTemplateRepository = Depends(get_template_repository),
    current_user: JWTPayload = Depends(get_current_user),
):
    """Lista todos los templates del usuario autenticado."""
    try:
        user_id = current_user["user_id"]
        use_case = ListTimesheetTemplatesUseCase(repository)
        templates = use_case.execute(user_id)

        return [
            TimesheetTemplateResponse(
                id=t.id if t.id is not None else 0,
                user_id=t.user_id,
                name=t.name,
                project_id=t.project_id,
                task_id=t.task_id,
                created_at=t.created_at,
            )
            for t in templates
            if t.id is not None
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al listar los templates: {str(e)}"
        )


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: int,
    repository: TimesheetTemplateRepository = Depends(get_template_repository),
    current_user: JWTPayload = Depends(get_current_user),
):
    """Elimina un template del usuario autenticado."""
    try:
        user_id = current_user["user_id"]
        use_case = DeleteTimesheetTemplateUseCase(repository)
        use_case.execute(template_id, user_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al eliminar el template: {str(e)}"
        )
