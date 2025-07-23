from fastapi import APIRouter, Depends, HTTPException
from app.email.api.schemas import SupportMailRequest, ReviewMailRequest
from app.email.api.dependencies import (
    get_email_service_dependency,
    get_timesheet_line_gateway_dependency,
)
from app.shared.security.dependencies import get_current_user
from app.timesheet_line.domain.repositories import TimesheetLineGateway

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/support-mail")
async def send_support_mail(
    request: SupportMailRequest, 
    email_service=Depends(get_email_service_dependency),
    current_user: dict = Depends(get_current_user),
):
    try:
        await email_service.send_support_mail(
            request.user_name, 
            request.subject, 
            request.body, 
            request.date
        )
        return {"message": "Mail enviado correctamente!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/review-mail")
async def review_mail(
    request: ReviewMailRequest,
    email_service=Depends(get_email_service_dependency),
    timesheet_line_gateway: TimesheetLineGateway = Depends(
        get_timesheet_line_gateway_dependency
    ),
    current_user: dict = Depends(get_current_user),
):
    try:
        await email_service.send_review_mail(
            request.user_mail,
            request.timesheetline_ids,
            timesheet_line_gateway,
            request.body,
        )
        return {"message": "Mail enviado correctamente!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
