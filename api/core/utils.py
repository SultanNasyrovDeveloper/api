
def flatten_ancestors(parent: dict, key: str) -> list[dict]:
    flattened = []
    current = parent
    while current:
        if isinstance(current, list):
            current = current[0] if len(current) else {}
        nested = current.pop(key)
        flattened.append(current)
        current = nested
    return flattened[::-1]
