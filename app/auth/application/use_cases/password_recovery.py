from app.auth.application.dto.password_recovery import (
    RequestOTPDTO,
    VerifyOTPDTO,
    ResetPasswordDTO,
)
from app.auth.application.services.otp_service import OTPService
from app.auth.application.use_cases.exceptions.exceptions import (
    OTPNotFound,
    PasswordNotMatch,
    UserNotFound,
)
from app.auth.domain.repositories import OTPRepository
from app.auth.infra.email_service import EmailService
from app.auth.infra.password_service import PasswordService
from app.users.domain.repositories import UserRepository


class PasswordRecoveryUseCase:
    def __init__(
        self,
        user_repository: UserRepository,
        email_service: EmailService,
        password_service: PasswordService,
        otp_repository: OTPRepository,
    ):
        self.user_repository = user_repository
        self.otp_repository = otp_repository
        self.email_service = email_service
        self.password_service = password_service
        self.otp_service = OTPService()

    async def request_otp(self, dto: RequestOTPDTO) -> bool:
        user = self.user_repository.get_by_email(dto.email)
        if not user or user.id is None:
            raise UserNotFound("El usuario no existe")

        # Generar código OTP
        new_otp = self.otp_service.create_otp(int(user.id))
        await self.otp_repository.save(new_otp)

        # Enviar email con el código
        await self.email_service.send_otp_email(dto.email, new_otp.code)
        return True

    async def verify_otp(self, dto: VerifyOTPDTO) -> bool:
        user = self.user_repository.get_by_email(dto.email)
        if not user or user.id is None:
            raise UserNotFound("El usuario no existe")
        otp = self.otp_repository.get_valid_otp(int(user.id), dto.code)
        if not otp:
            raise OTPNotFound("El código OTP no es válido")
        return True

    async def reset_password(self, dto: ResetPasswordDTO) -> bool:
        if dto.new_password != dto.confirm_password:
            raise PasswordNotMatch("Las contraseñas no coinciden")
        user = self.user_repository.get_by_email(dto.email)
        if not user or user.id is None:
            raise UserNotFound("El usuario no existe")
        otp = self.otp_repository.get_valid_otp(int(user.id), dto.code)
        if not otp:
            raise OTPNotFound("El código OTP no es válido")
        # Hashear nueva contraseña
        hashed_password = self.password_service.hash_password(dto.new_password)
        # Actualizar contraseña y marcar OTP como usado
        self.user_repository.update_password(int(user.id), hashed_password)
        if otp.id is not None:  # Verificar que el ID existe
            self.otp_repository.mark_otp_as_used(otp.id)
        return True
