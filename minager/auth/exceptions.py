class AuthError(Exception):
    """Base class for domain errors raised by the auth service layer."""


class EmailAlreadyRegisteredError(AuthError):
    def __init__(self):
        super().__init__('Email already registered')


class UsernameAlreadyTakenError(AuthError):
    def __init__(self):
        super().__init__('Username already taken')


class UserNotFoundError(AuthError):
    def __init__(self):
        super().__init__('User not found')


class ProfileNotFoundError(AuthError):
    def __init__(self):
        super().__init__('Profile not found')


class KnowledgeTreeProvisioningError(AuthError):
    def __init__(self):
        super().__init__('Unable to create knowledge tree root.')


class InvalidTokenError(AuthError):
    def __init__(self):
        super().__init__('Could not validate credentials')


class InvalidTokenTypeError(AuthError):
    def __init__(self):
        super().__init__('Could not validate credentials')
