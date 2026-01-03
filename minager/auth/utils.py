from datetime import UTC, datetime


def utc_now_naive() -> datetime:
    """Get current UTC time as timezone-naive datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE"""
    return datetime.now(UTC).replace(tzinfo=None)
