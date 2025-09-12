from enum import IntEnum


class ProjectStages(IntEnum):
    """Etapas de proyecto y sus IDs en entorno de desarrollo/local.

    Ajusta los valores si en DEV/LOCAL cambian los IDs de Odoo.

    Basado en los datos obtenidos del script de prueba:
    - To Do: ID 1
    - In Progress: ID 2
    - Done: ID 3
    - Cancelled: ID 4
    """

    TO_DO = 1
    IN_PROGRESS = 2
    DONE = 3
    CANCELLED = 4

    @classmethod
    def active_stages(cls) -> list[int]:
        """Devuelve los IDs de las etapas activas (To Do e In Progress)."""
        return [int(cls.TO_DO), int(cls.IN_PROGRESS)]

    @classmethod
    def inactive_stages(cls) -> list[int]:
        """Devuelve los IDs de las etapas inactivas (Done y Cancelled)."""
        return [int(cls.DONE), int(cls.CANCELLED)]
