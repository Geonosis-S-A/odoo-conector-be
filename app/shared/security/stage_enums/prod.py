from enum import IntEnum


class ProjectStages(IntEnum):
    """Etapas de proyecto y sus IDs en entorno de producción.

    Ajusta los valores si en PROD cambian los IDs de Odoo.

    NOTA: Estos valores deben ser configurados según la instancia de producción.
    Los valores aquí son placeholder y deben ser actualizados con los IDs reales.
    """

    TO_DO = 1  # Placeholder - actualizar con el ID real de producción
    IN_PROGRESS = 2  # Placeholder - actualizar con el ID real de producción
    DONE = 3  # Placeholder - actualizar con el ID real de producción
    CANCELLED = 4  # Placeholder - actualizar con el ID real de producción

    @classmethod
    def active_stages(cls) -> list[int]:
        """Devuelve los IDs de las etapas activas (To Do e In Progress)."""
        return [int(cls.TO_DO), int(cls.IN_PROGRESS)]

    @classmethod
    def inactive_stages(cls) -> list[int]:
        """Devuelve los IDs de las etapas inactivas (Done y Cancelled)."""
        return [int(cls.DONE), int(cls.CANCELLED)]
