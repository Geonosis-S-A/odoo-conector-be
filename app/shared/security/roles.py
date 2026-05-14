import os


def load_roles_enum():
    """Carga el enum de roles adecuado según ENV y lo expone como Roles.

    - ENV=STAGING -> app.shared.security.role_enums.staging.Roles
    - por defecto -> app.shared.security.role_enums.dev.Roles
    """

    env_value = os.getenv("ENV", "LOCAL").upper()
    if env_value == "STAGING":
        from app.shared.security.role_enums.staging import Roles as RolesEnum
    else:
        from app.shared.security.role_enums.dev import Roles as RolesEnum
    return RolesEnum


# Export público: Roles apunta al enum del entorno actual
Roles = load_roles_enum()


def user_has_role(user_roles: list[int] | None, role: int) -> bool:
    """Verifica si el usuario posee el rol especificado.

    user_roles puede ser None.
    """

    if not user_roles:
        return False
    return int(role) in user_roles


def is_privileged_user(user_roles: list[int] | None) -> bool:
    """True si el usuario posee el rol approver.

    Usado como gate para datos sensibles: directorio completo de empleados,
    roles expuestos en sync, etc. Falla cerrado (False) si user_roles es
    None o vacío.
    """
    if not user_roles:
        return False
    return int(Roles.approver) in user_roles
