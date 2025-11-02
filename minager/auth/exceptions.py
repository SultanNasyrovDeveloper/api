from fastapi.exceptions import HTTPException


class UserNotFoundException(HTTPException):
    pass


class UserAlreadyExistsException(HTTPException):
    pass
