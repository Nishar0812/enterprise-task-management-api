from datetime import datetime, timezone

from app.extensions.database import TZDateTime, db

STATUS_VALUES = ("pending", "in_progress", "completed")
PRIORITY_VALUES = ("low", "medium", "high")


class Task(db.Model):
    __tablename__ = "tasks"
    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed')", name="ck_tasks_status"
        ),
        db.CheckConstraint(
            "priority IN ('low', 'medium', 'high')", name="ck_tasks_priority"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    priority = db.Column(db.String(20), nullable=False, default="medium")
    project_id = db.Column(db.Integer, db.ForeignKey("projects.id"), nullable=False, index=True)
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    created_at = db.Column(
        TZDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        TZDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    project = db.relationship("Project", back_populates="tasks", foreign_keys=[project_id])
    assignee = db.relationship("User", back_populates="assigned_tasks", foreign_keys=[assigned_to])

    def __repr__(self) -> str:
        return f"<Task id={self.id} title={self.title}>"
