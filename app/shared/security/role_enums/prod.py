from enum import IntEnum


class Roles(IntEnum):
    """Roles lógicos y sus IDs en entorno de producción.

    Ajusta los valores si en PROD cambian los IDs de Odoo.

    approver = 80: grupo "Hojas de trabajo / Administrador" de res.groups
    (el mismo id que usa el front en producción).
    """

    approver = 80
