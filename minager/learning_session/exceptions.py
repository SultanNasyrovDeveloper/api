class LearningSessionError(Exception):
    """Base class for domain errors raised by the learning_session service layer."""


class SessionNotFoundError(LearningSessionError):
    def __init__(self):
        super().__init__('Learning session not found')


class EmptyQueueError(LearningSessionError):
    """No node in the target subtrees matched the requested filter strategy.

    Starting a session here would persist one with an empty queue, which blocks every
    later `start` call until it expires or is finished explicitly.
    """

    def __init__(self):
        super().__init__('No nodes match the requested filter strategy')
