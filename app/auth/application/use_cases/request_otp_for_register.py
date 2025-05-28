from datetime import datetime, timedelta
import random
import string
from typing import Any
from app.auth.domain.models import OTPModel
from app.auth.infra.email_service import EmailService
from app.users.domain.models import User
from app.users.domain.repositories import EmployeeGateway, UserRepository


class RequestOTPForRegisterUseCase:
    def __init__(
        self,
        employee_gateway: EmployeeGateway,
        user_repository: UserRepository,
        otp_repository: Any,
        email_service: EmailService,
    ):
        self.employee_gateway = employee_gateway
        self.user_repository = user_repository
        self.email_service = email_service
        self.otp_repository = otp_repository

    def generate_otp(self) -> str:
        return "".join(random.choices(string.digits, k=6))

    async def execute(self, email: str) -> bool:
        # Todo: Pensar si es necesario que si ya esta en nuestra bbdd que tire error o que lo ignore.
        employee = self.employee_gateway.get_by_email(email)
        if not employee:
            return False
        if employee.id is None:
            return False

        # Crear usuario en nuestra bbdd
        user = User(
            id=employee.id,
            email=employee.email,
            full_name=employee.full_name,
            is_active=False,
            is_superuser=False,
        )
        self.user_repository.save(user)

        # Generar código OTP
        otp_code = self.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        # Guardar OTP en la base de datos
        otp = OTPModel(
            user_id=int(employee.id),
            code=otp_code,
            expires_at=expires_at,
            is_used=False,
        )
        await self.otp_repository.save_otp(otp)

        # Enviar email con el código
        await self.email_service.send_otp_email(employee.email, otp_code)
        return True
