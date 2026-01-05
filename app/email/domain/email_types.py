from enum import Enum


class TimesheetEmailType(str, Enum):
    """Tipos de email relacionados con timesheets"""
    APPROVED = "approved"
    REVIEW = "review"
    ELIMINATED = "eliminated"

