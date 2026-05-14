from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from app.email.domain.email_types import TimesheetEmailType


class SupportMailRequest(BaseModel):
    """Sólo contenido del reporte; identidad viene del JWT (VT-09)."""

    model_config = ConfigDict(extra="forbid")

    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1, max_length=20000)


class ApprovedMailRequest(BaseModel):
    approver_mail: str
    timesheetline_ids: list[int]

class ReviewMailRequest(ApprovedMailRequest):
    body: Optional[str] = None
    email_type: Optional[TimesheetEmailType]
