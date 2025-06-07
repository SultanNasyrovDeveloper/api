from datetime import datetime


def to_surreal_datetime_string(dt: datetime) -> str:
    return f'd"{dt.strftime('%Y-%m-%dT%H:%M:%SZ')}"'
