class UserError(Exception):
    """Base class for domain errors raised by the user service layer."""


class EmailAlreadyRegisteredError(UserError):
    def __init__(self):
        super().__init__('Email already registered')


class UsernameAlreadyTakenError(UserError):
    def __init__(self):
        super().__init__('Username already taken')


class UserNotFoundError(UserError):
    def __init__(self):
        super().__init__('User not found')


class ProfileNotFoundError(UserError):
    def __init__(self):
        super().__init__('Profile not found')


class KnowledgeTreeProvisioningError(UserError):
    def __init__(self):
        super().__init__('Unable to create knowledge tree root.')
