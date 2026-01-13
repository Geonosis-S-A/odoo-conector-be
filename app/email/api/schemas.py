from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.email.domain.email_types import TimesheetEmailType


class SupportMailRequest(BaseModel):
    user_name: str
    subject: str
    body: str
    date: datetime

class ApprovedMailRequest(BaseModel):
    approver_mail: str
    timesheetline_ids: list[int]

class ReviewMailRequest(ApprovedMailRequest):
    body: Optional[str] = None
    email_type: Optional[TimesheetEmailType]
