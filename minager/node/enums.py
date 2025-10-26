from enum import IntEnum


class NodeRelationType(IntEnum):
    first_child = 1
    last_child = 2
    before = 3
    after = 4


class MovePosition(IntEnum):
    first_child = 1
    last_child = 2
    left = 3
    right = 4


class NodeOrdering(IntEnum):
    random = 1
    outdated = 2

    breadth_first = 3
    depth_first = 4

    with_zero_owner_views = 5
    with_zero_size = 6
