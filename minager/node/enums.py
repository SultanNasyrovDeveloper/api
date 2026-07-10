from enum import IntEnum, StrEnum


class SubtreeFilter(StrEnum):
    """Narrows which nodes of a subtree are returned. Never affects their order."""

    all = 'all'
    due = 'due'
    struggling = 'struggling'
    never_reviewed = 'never_reviewed'
    empty = 'empty'


class TraversalOrder(StrEnum):
    """Order in which a subtree is walked. Decides which nodes survive a LIMIT."""

    bfs = 'bfs'
    dfs = 'dfs'
    random = 'random'


class NodeRelationType(IntEnum):
    first_child = 1
    last_child = 2
    before = 3
    after = 4


class MovePosition(IntEnum):
    first_child = 1
    last_child = 2
    before = 3
    after = 4
