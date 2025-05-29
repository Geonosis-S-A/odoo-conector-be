from app.auth.application.services.otp_service import OTPService
from app.auth.application.use_cases.exceptions.exceptions import (
    EmployeeNotFound,
    UserAlreadyExists,
)
from app.auth.domain.repositories import OTPRepository
from app.auth.infra.email_service import EmailService
from app.users.domain.models import User
from app.users.domain.repositories import EmployeeGateway, UserRepository


class RequestOTPForRegisterUseCase:
    def __init__(
        self,
        employee_gateway: EmployeeGateway,
        user_repository: UserRepository,
        otp_repository: OTPRepository,
        email_service: EmailService,
    ):
        self.employee_gateway = employee_gateway
        self.user_repository = user_repository
        self.email_service = email_service
        self.otp_repository = otp_repository
        self.otp_service = OTPService()

    async def execute(self, email: str) -> bool:
        employee = self.employee_gateway.get_by_email(email)
        if not employee:
            raise EmployeeNotFound("El email no ha sido registrado en el sistema")

        # Validamos si el email ya existe en nuestra bbdd
        bd_user = self.user_repository.get_by_email(email)
        if bd_user:
            raise UserAlreadyExists("El email ya ha sido registrado en el sistema.")

        # Creamos el usuario en nuestra bbdd
        user = User(
            id=employee.id,
            email=employee.email,
            full_name=employee.full_name,
            is_active=False,
            is_superuser=False,
        )
        self.user_repository.save(user)

        # Generamos el código OTP
        new_otp = self.otp_service.create_otp(int(employee.id))
        await self.otp_repository.save(new_otp)

        # Enviamos el email con el código OTP
        await self.email_service.send_otp_email(employee.email, new_otp.code)
        return True
