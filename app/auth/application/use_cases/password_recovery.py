from datetime import datetime, timedelta
import random
import string
from typing import Optional

from app.auth.application.dto.password_recovery import (
    RequestOTPDTO,
    VerifyOTPDTO,
    ResetPasswordDTO,
)
from app.auth.domain.repositories import UserRepository
from app.auth.infra.db.models import OTPModel
from app.auth.infra.email_service import EmailService
from app.auth.infra.password_service import PasswordService


class PasswordRecoveryUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        email_service: EmailService,
        password_service: PasswordService,
    ):
        self.user_repository = user_repository
        self.email_service = email_service
        self.password_service = password_service

    def generate_otp(self) -> str:
        return "".join(random.choices(string.digits, k=6))

    async def request_otp(self, dto: RequestOTPDTO) -> bool:
        user = await self.user_repository.get_by_email(dto.email)
        if not user or user.id is None:
            return False

        # Generar código OTP
        otp_code = self.generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=15)

        # Guardar OTP en la base de datos
        otp = OTPModel(
            user_id=int(user.id), code=otp_code, expires_at=expires_at, is_used=False
        )
        await self.user_repository.save_otp(otp)

        # Enviar email con el código
        await self.email_service.send_otp_email(dto.email, otp_code)
        return True

    async def verify_otp(self, dto: VerifyOTPDTO) -> bool:
        user = await self.user_repository.get_by_email(dto.email)
        if not user or user.id is None:
            return False
        otp = await self.user_repository.get_valid_otp(int(user.id), dto.code)
        if not otp:
            return False
        return True

    async def reset_password(self, dto: ResetPasswordDTO) -> bool:
        if dto.new_password != dto.confirm_password:
            return False
        user = await self.user_repository.get_by_email(dto.email)
        if not user or user.id is None:
            return False
        otp = await self.user_repository.get_valid_otp(int(user.id), dto.code)
        if not otp:
            return False
        # Hashear nueva contraseña
        hashed_password = self.password_service.hash_password(dto.new_password)
        # Actualizar contraseña y marcar OTP como usado
        await self.user_repository.update_password(int(user.id), hashed_password)
        if otp.id is not None:  # Verificar que el ID existe
            await self.user_repository.mark_otp_as_used(otp.id)
        return True
