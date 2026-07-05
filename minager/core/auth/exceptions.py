class AuthError(Exception):
    """Base class for domain errors raised while verifying tokens."""


class InvalidTokenError(AuthError):
    def __init__(self):
        super().__init__('Could not validate credentials')


class InvalidTokenTypeError(AuthError):
    def __init__(self):
        super().__init__('Could not validate credentials')
