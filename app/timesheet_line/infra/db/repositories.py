from sqlmodel import Session, desc, select
from app.timesheet_line.domain.models import (
    CreateTimesheetLineNotification,
    TimesheetLineNotification,
)
from app.timesheet_line.domain.repositories import TimesheetLineNotificationRepository
from app.timesheet_line.infra.db.models import TimesheetLineNotificationModel


class SQLModelTimesheetLineNotificationRepository(TimesheetLineNotificationRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, timesheet_line_notification: CreateTimesheetLineNotification
    ) -> bool:
        db_timesheet_line_notification = TimesheetLineNotificationModel(
            timesheet_line_id=timesheet_line_notification.timesheet_line_id,
            approver_id=timesheet_line_notification.approver_id,
            receiver_id=timesheet_line_notification.receiver_id,
        )
        self.db.add(db_timesheet_line_notification)
        self.db.commit()
        return True

    def get_by_timesheet_id(
        self, timesheet_line_id: int
    ) -> TimesheetLineNotification | None:
        # Puede haber varias, devuelvo la de creación más reciente
        db_timesheet_line_notification = self.db.exec(
            select(TimesheetLineNotificationModel)
            .where(
                TimesheetLineNotificationModel.timesheet_line_id == timesheet_line_id
            )
            .order_by(desc(TimesheetLineNotificationModel.created_at))
        ).first()

        if db_timesheet_line_notification is None:
            return None
        if db_timesheet_line_notification.id is None:
            return None

        return TimesheetLineNotification(
            id=db_timesheet_line_notification.id,
            timesheet_line_id=db_timesheet_line_notification.timesheet_line_id,
            approver_id=db_timesheet_line_notification.approver_id,
            receiver_id=db_timesheet_line_notification.receiver_id,
            created_at=db_timesheet_line_notification.created_at,
        )

    def delete(self, timesheet_line_notification_id: int) -> bool:
        db_timesheet_line_notification = self.db.get(
            TimesheetLineNotificationModel, timesheet_line_notification_id
        )
        if db_timesheet_line_notification is None:
            return False
        self.db.delete(db_timesheet_line_notification)
        self.db.commit()
        return True
