from enum import IntEnum


class Roles(IntEnum):
    """Roles lógicos y sus IDs en entorno de staging.

    Ajusta los valores si en STAGING cambian los IDs de Odoo.
    """

    approver = 80
