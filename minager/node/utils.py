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


def construct_tree(nodes: list[dict]) -> dict:
    """
    Generates tree like structure where each node has list of its children from
    flat database list of nodes based on id and parent_id fields.
    """
    if not isinstance(nodes, list):
        return nodes

    if not len(nodes):
        return {}

    root = nodes[0]
    tree = {'id': root['id'].id, 'data': root, 'children': {}}

    def get_node_from_tree(id_: str, subtree: dict) -> dict | None:
        if id_ == subtree['id']:
            return subtree
        if id_ in subtree['children']:
            return subtree['children'][id_]
        for node_data in subtree['children'].values():
            maybe_target_node = get_node_from_tree(id_, node_data)
            if maybe_target_node:
                return maybe_target_node
        return None

    for node in nodes[1:]:
        node_id = node['id'].id
        parent_id = node['parent_id'].id
        parent = get_node_from_tree(parent_id, tree)
        if parent:
            parent['children'][node_id] = {'id': node_id, 'data': node, 'children': {}}

    def make_children_list(obj: dict):
        return {
            **obj['data'],
            'children': sorted(map(make_children_list, obj['children'].values()), key=lambda n: n['order']),
        }

    final_tree = make_children_list(tree)
    return final_tree
