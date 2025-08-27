from fastapi import APIRouter, Depends, HTTPException
from app.email.api.dependencies import get_common_email_service
from app.email.api.schemas import SupportMailRequest
from app.email.infra.email_service import CommonResendEmailService
from app.shared.security.dependencies import get_current_user

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/support-mail")
async def send_support_mail(
    request: SupportMailRequest,
    email_service: CommonResendEmailService = Depends(get_common_email_service),
    current_user: dict = Depends(get_current_user),
):
    try:
        await email_service.send_support_mail(
            request.user_name, request.subject, request.body, request.date
        )
        return {"message": "Mail enviado correctamente!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
