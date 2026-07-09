class RepetitionAssistantError(Exception):
    """Base class for domain errors raised by the repetition_assistant service layer."""


class ReviewNotFoundError(RepetitionAssistantError):
    def __init__(self):
        super().__init__('Repetition assistant review not found')
