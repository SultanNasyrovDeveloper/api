from pwdlib import PasswordHash


class PasswordService:
    def __init__(self, password_hash: PasswordHash):
        self.password_hash = password_hash

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.password_hash.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        return self.password_hash.hash(password)
