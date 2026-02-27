from typing import List, Optional
from sqlmodel import Session, select, col
from app.timesheet_templates.domain.models import TimesheetTemplate
from app.timesheet_templates.domain.repositories import TimesheetTemplateRepository
from app.timesheet_templates.infra.db.models import TimesheetTemplateModel


class SQLModelTimesheetTemplateRepository(TimesheetTemplateRepository):
    """Implementación del repositorio usando SQLModel."""

    def __init__(self, session: Session):
        self.session = session

    def create(self, template: TimesheetTemplate) -> TimesheetTemplate:
        """Crea un nuevo template en la base de datos."""
        db_template = TimesheetTemplateModel(
            user_id=template.user_id,
            name=template.name,
            project_id=template.project_id,
            task_id=template.task_id,
            created_at=template.created_at,
        )

        self.session.add(db_template)
        self.session.commit()
        self.session.refresh(db_template)

        return self._to_domain(db_template)

    def list_by_user(self, user_id: int) -> List[TimesheetTemplate]:
        """Lista todos los templates de un usuario, ordenados por fecha de creación (más recientes primero)."""
        statement = (
            select(TimesheetTemplateModel)
            .where(TimesheetTemplateModel.user_id == user_id)
            .order_by(col(TimesheetTemplateModel.created_at).desc())
        )

        results = self.session.exec(statement).all()
        return [self._to_domain(db_template) for db_template in results]

    def delete(self, template_id: int, user_id: int) -> bool:
        """Elimina un template si pertenece al usuario."""
        statement = select(TimesheetTemplateModel).where(
            TimesheetTemplateModel.id == template_id,
            TimesheetTemplateModel.user_id == user_id,
        )

        db_template = self.session.exec(statement).first()

        if not db_template:
            raise ValueError(
                f"Template con ID {template_id} no existe o no pertenece al usuario"
            )

        self.session.delete(db_template)
        self.session.commit()
        return True

    def get_by_id(self, template_id: int) -> Optional[TimesheetTemplate]:
        """Obtiene un template por su ID."""
        statement = select(TimesheetTemplateModel).where(
            TimesheetTemplateModel.id == template_id
        )
        db_template = self.session.exec(statement).first()

        if not db_template:
            return None

        return self._to_domain(db_template)

    def _to_domain(self, db_template: TimesheetTemplateModel) -> TimesheetTemplate:
        """Convierte un modelo de DB a entidad de dominio."""
        return TimesheetTemplate(
            id=db_template.id,
            user_id=db_template.user_id,
            name=db_template.name,
            project_id=db_template.project_id,
            task_id=db_template.task_id,
            created_at=db_template.created_at,
        )
