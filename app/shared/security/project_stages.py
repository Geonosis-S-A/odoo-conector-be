import os


def load_project_stages_enum():
    """Carga el enum de etapas de proyecto adecuado según ENV.

    - ENV=STAGING -> app.shared.security.stage_enums.staging.ProjectStages
    - ENV=PROD -> app.shared.security.stage_enums.prod.ProjectStages
    - por defecto -> app.shared.security.stage_enums.dev.ProjectStages
    """

    env_value = os.getenv("ENV", "LOCAL").upper()
    if env_value == "STAGING":
        from app.shared.security.stage_enums.staging import (
            ProjectStages as ProjectStagesEnum,
        )
    elif env_value == "PROD":
        from app.shared.security.stage_enums.prod import (
            ProjectStages as ProjectStagesEnum,
        )
    else:
        from app.shared.security.stage_enums.dev import (
            ProjectStages as ProjectStagesEnum,
        )
    return ProjectStagesEnum


# Export público: ProjectStages apunta al enum del entorno actual
ProjectStages = load_project_stages_enum()


def is_active_stage(stage_id: int) -> bool:
    """Verifica si una etapa está activa (To Do o In Progress).

    Args:
        stage_id: ID de la etapa a verificar

    Returns:
        bool: True si la etapa está activa, False en caso contrario
    """
    return stage_id in ProjectStages.active_stages()


def is_inactive_stage(stage_id: int) -> bool:
    """Verifica si una etapa está inactiva (Done o Cancelled).

    Args:
        stage_id: ID de la etapa a verificar

    Returns:
        bool: True si la etapa está inactiva, False en caso contrario
    """
    return stage_id in ProjectStages.inactive_stages()


def get_stage_name(stage_id: int) -> str:
    """Obtiene el nombre legible de una etapa por su ID.

    Args:
        stage_id: ID de la etapa

    Returns:
        str: Nombre de la etapa o 'Unknown' si no se encuentra
    """
    stage_mapping = {
        ProjectStages.TO_DO: "To Do",
        ProjectStages.IN_PROGRESS: "In Progress",
        ProjectStages.DONE: "Done",
        ProjectStages.CANCELLED: "Cancelled",
    }
    return stage_mapping.get(stage_id, "Unknown")
