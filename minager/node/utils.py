def get_string_size_in_bytes(string: str) -> int:
    return len(string.encode('utf-8'))


def get_content_size(root: dict) -> int:
    size = 0
    if root.get('text'):
        size += get_string_size_in_bytes(root.get('text', ''))
    for child in root.get('children', []):
        size += get_content_size(child)
    return size


def parse_id(id_: str) -> list[str]:
    return id_.split(':')
