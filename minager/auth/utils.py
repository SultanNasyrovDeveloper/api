def to_unix_timestamp(python_timestamp: int | float) -> int:
    return int(python_timestamp * 1000)
