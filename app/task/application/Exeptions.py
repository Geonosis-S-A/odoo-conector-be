class ProjectErrors(Exception):
    """Excepción base para errores del dominio de timesheet."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class ProjectNotFound(ProjectErrors):
    """Error cuando no se encuentra un proyecto."""

    def __init__(self, project_id: int):
        message = f"Proyecto con el id {project_id} no encontrado."
        super().__init__(message)

class TasksNotFound_projectId(ProjectErrors):
    """Error cuando no se encuentran tareas de un proyecto."""

    def __init__(self, project_id: int):
        message = f"Tareas del proyecto con el id {project_id} no encontradas."
        super().__init__(message)

class TasksNotFound_userId(ProjectErrors):
    """Error cuando no se encuentran tareas de un usuario."""

    def __init__(self, user_id: int):
        message = f"Tareas del usuario con el id {user_id} no encontradas."
        super().__init__(message)

class ProjectsNotFound(ProjectErrors):
    """Error cuando no se encuentran proyectos."""

    def __init__(self):
        message = f"No hay proyectos asignados."
        super().__init__(message)

