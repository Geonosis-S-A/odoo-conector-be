from enum import IntEnum


class ProjectStages(IntEnum):
    """Etapas de proyecto y sus IDs en entorno de staging.

    Ajusta los valores si en STAGING cambian los IDs de Odoo.

    NOTA: Estos valores deben ser configurados según la instancia de staging.
    Los valores aquí son placeholder y deben ser actualizados con los IDs reales.
    """

    TO_DO = 1  # Placeholder - actualizar con el ID real de staging
    IN_PROGRESS = 2  # Placeholder - actualizar con el ID real de staging
    DONE = 3  # Placeholder - actualizar con el ID real de staging
    CANCELLED = 4  # Placeholder - actualizar con el ID real de staging

    @classmethod
    def active_stages(cls) -> list[int]:
        """Devuelve los IDs de las etapas activas (To Do e In Progress)."""
        return [int(cls.TO_DO), int(cls.IN_PROGRESS)]

    @classmethod
    def inactive_stages(cls) -> list[int]:
        """Devuelve los IDs de las etapas inactivas (Done y Cancelled)."""
        return [int(cls.DONE), int(cls.CANCELLED)]
