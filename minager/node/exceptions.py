class NodeError(Exception):
    """Base class for domain errors raised by the node service layer."""


class NodeNotFoundError(NodeError):
    def __init__(self):
        super().__init__('Node not found')
