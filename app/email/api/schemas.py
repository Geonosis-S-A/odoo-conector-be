from pydantic import BaseModel
from datetime import datetime

class SupportMailRequest(BaseModel):
    user_name: str
    subject: str
    body: str
    date: datetime