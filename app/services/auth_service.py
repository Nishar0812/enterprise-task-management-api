from app.extensions.database import db
from app.models.user import User
from app.services.authorization_service import require_permission


class EmailAlreadyRegisteredError(Exception):
    """Raised when attempting to register an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match a known, active user."""


class UserNotFoundError(Exception):
    """Raised when a requested user does not exist."""


class LastAdminError(Exception):
    """Raised when an operation would leave the system without an admin."""


def register_user(*, name: str, email: str, password: str) -> User:
    if User.query.filter_by(email=email).first() is not None:
        raise EmailAlreadyRegisteredError()

    user = User(name=name, email=email, role="member")
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return user


def authenticate_user(*, email: str, password: str) -> User:
    user = User.query.filter_by(email=email).first()
    if user is None or not user.check_password(password):
        raise InvalidCredentialsError()

    return user


def get_user_by_id(user_id: int) -> User | None:
    return db.session.get(User, user_id)


def change_user_role(*, actor: User, user_id: int, new_role: str) -> User:
    require_permission(actor, "user:change_role")

    user = db.session.get(User, user_id)
    if user is None:
        raise UserNotFoundError()

    if user.role == "admin" and new_role != "admin":
        admins = User.query.filter_by(role="admin").with_for_update().all()
        if len(admins) <= 1:
            raise LastAdminError()

    user.role = new_role
    db.session.commit()
    return user
