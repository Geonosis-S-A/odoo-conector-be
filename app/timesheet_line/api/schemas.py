from typing import Optional, List
from pydantic import BaseModel, field_validator
from datetime import date, datetime

from app.project.api.schemas import ProjectResponse
from app.task.api.schemas import TaskInfoResponse
from app.shared.security.url_safety import safe_text_validator


class CargarHorasRequest(BaseModel):
    name: Optional[str] | None = None
    employee_id: int
    project_id: int
    hours: float
    date: date
    task_id: int | None = None

    # VT-12 (pentest 2026-04, GEO-1388): el campo `name` es texto libre que
    # luego se persiste en Odoo. Bloqueamos URLs hacia recursos internos
    # (link-local, RFC 1918, loopback, cloud metadata) en cualquier
    # representación (decimal 32-bit, hex, octal, IPv6 mapped). El filtro
    # previo era a nivel LLM y se bypasseaba con IP decimal.
    @field_validator("name")
    @classmethod
    def _validate_name_safe(cls, v: Optional[str]) -> Optional[str]:
        return safe_text_validator(v)


class TimesheetLineNotificationResponse(BaseModel):
    id: int
    sender_name: str
    sended_at: datetime


class DetailedTimesheetLineResponse(BaseModel):
    id: int
    name: str
    employee_id: int
    project: ProjectResponse
    task: Optional[TaskInfoResponse]
    hours: float
    date: date
    create_date: Optional[datetime] = None
    validated: bool
    notification: Optional[TimesheetLineNotificationResponse] = None


class EditTimesheetRequest(BaseModel):
    id: int
    name: str
    employee_id: int
    project_id: int
    hours: float
    date: date
    task_id: Optional[int] = None
    validated: bool

    # VT-12 (pentest 2026-04, GEO-1388): mismo bloqueo que en CargarHorasRequest.
    @field_validator("name")
    @classmethod
    def _validate_name_safe(cls, v: str) -> str:
        return safe_text_validator(v) or ""


class DeleteTimesheetRequest(BaseModel):
    ids: List[int]


class ValidateTimesheetRequest(BaseModel):
    timesheetline_ids: List[int]
