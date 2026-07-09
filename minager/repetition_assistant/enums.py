from enum import StrEnum


class MessageRole(StrEnum):
    assistant = 'assistant'
    user = 'user'


class MessageType(StrEnum):
    default = 'default'
    question = 'question'
    verdict = 'verdict'
