from fastapi import HTTPException
from app.auth.application.services.crypt_service import BcryptPasswordService
from app.auth.domain.repositories import UserCredentialsRepository
from app.auth.infra.auth_service import TokenService


class ChangePasswordUseCase:
    def __init__(
        self,
        password_service: BcryptPasswordService,
        user_credentials_repository: UserCredentialsRepository,
    ):
        self.password_service = password_service
        self.user_credentials_repository = user_credentials_repository

    def execute(self, user_id: int, current_password: str, new_password: str) -> bool:
        """Ejecuta el caso de uso para cambiar la contraseña de un usuario.

        Args:
            user_id: ID del usuario
            current_password: Contraseña actual del usuario
            new_password: Nueva contraseña del usuario

        Returns:
            bool: True si el cambio fue exitoso, False en caso contrario

        Raises:
            HTTPException: Si las credenciales son inválidas o el usuario no existe
        """
        # 1. Obtener las credenciales del usuario por ID
        try:
            user_credentials = self.user_credentials_repository.get_user_by_id(user_id)
        except HTTPException:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")

        # 2. Verificar que el usuario esté activo
        if not user_credentials.is_active:
            raise HTTPException(status_code=401, detail="Usuario inactivo")

        # 3. Verificar que la contraseña actual sea correcta
        if not self.password_service.verify_password(
            current_password, user_credentials.password
        ):
            raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")

        # 4. Validar que la nueva contraseña no sea igual a la actual
        if self.password_service.verify_password(
            new_password, user_credentials.password
        ):
            raise HTTPException(
                status_code=400,
                detail="La nueva contraseña debe ser diferente a la actual",
            )

        # 5. Hashear la nueva contraseña
        new_hashed_password = self.password_service.hash_password(new_password)

        # 6. Actualizar la contraseña en la base de datos
        success = self.user_credentials_repository.update_password(
            user_id, new_hashed_password
        )

        if not success:
            raise HTTPException(
                status_code=500, detail="Error al actualizar la contraseña"
            )

        return True
