from datetime import datetime, timezone

from sqlalchemy import event
from sqlalchemy.orm import Session
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions.database import TZDateTime, db

ROLE_VALUES = ("admin", "manager", "member")


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint("role IN ('admin', 'manager', 'member')", name="ck_users_role"),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="member")
    created_at = db.Column(
        TZDateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at = db.Column(
        TZDateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    owned_projects = db.relationship(
        "Project", back_populates="owner", foreign_keys="Project.owner_id"
    )
    assigned_tasks = db.relationship(
        "Task", back_populates="assignee", foreign_keys="Task.assigned_to"
    )

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


@event.listens_for(Session, "before_flush")
def _prevent_delete_of_project_owner(session, flush_context, instances) -> None:
    for obj in session.deleted:
        if isinstance(obj, User) and obj.owned_projects:
            raise ValueError(
                f"Cannot delete user {obj.id}: still owns "
                f"{len(obj.owned_projects)} project(s). Reassign or delete those "
                "projects first."
            )
