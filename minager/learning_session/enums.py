from enum import IntEnum


class RepetitionStrategy(IntEnum):
    sm2 = 1


class TraverseStrategy(IntEnum):
    random = 1
    outdated = 2
    dfs = 3
    newest = 4
