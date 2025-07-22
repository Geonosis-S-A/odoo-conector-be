from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class SupportMailRequest(BaseModel):
    user_name: str
    subject: str
    body: str
    date: datetime

class ReviewMailRequest(BaseModel):
    user_mail: str
    body: Optional[str] = None
    timesheet_line_id: int