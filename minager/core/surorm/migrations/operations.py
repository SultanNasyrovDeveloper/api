from ..statements import Expression


class MigrationOperation:
    def __init__(self, query: Expression, reverse: Expression | None = None):
        self.query = query
        self.is_atomic: bool = False
        self.reverse = reverse
