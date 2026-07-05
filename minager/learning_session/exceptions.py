class LearningSessionError(Exception):
    """Base class for domain errors raised by the learning_session service layer."""


class SessionNotFoundError(LearningSessionError):
    def __init__(self):
        super().__init__('Learning session not found')
