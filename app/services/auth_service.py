from app.extensions.database import db
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    """Raised when attempting to register an email that already exists."""


class InvalidCredentialsError(Exception):
    """Raised when login credentials do not match a known, active user."""


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
