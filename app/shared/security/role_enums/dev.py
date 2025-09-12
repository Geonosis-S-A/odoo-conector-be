from enum import IntEnum


class Roles(IntEnum):
    """Roles lógicos y sus IDs en entorno de desarrollo/local.

    Ajusta los valores si en DEV/LOCAL cambian los IDs de Odoo.
    """

    approver = 31
