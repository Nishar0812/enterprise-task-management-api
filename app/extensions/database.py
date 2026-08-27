from datetime import datetime, timezone

from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator

db = SQLAlchemy()
migrate = Migrate()


class TZDateTime(TypeDecorator):
    """A DateTime column that always round-trips as UTC-aware.

    SQLite has no native timezone-aware timestamp type, so a plain
    ``DateTime(timezone=True)`` silently drops tzinfo on read. This
    normalizes to UTC on write and re-attaches UTC tzinfo on read so the
    Python-side value is timezone-aware on every supported backend.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is not None and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
