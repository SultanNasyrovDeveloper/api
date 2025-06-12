from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from jwt import ExpiredSignatureError, InvalidTokenError, decode, encode
from sqlalchemy.ext.asyncio import AsyncSession

from minager.core.db.managers import PostgresDatabaseManager
from minager.settings import config, crypt_context

from . import models, schemas, utils


class UserManager(PostgresDatabaseManager[models.User]):
    model_class = models.User

    async def add_user(
        self, create_user_data: dict | schemas.UserCreateDataSchema, session: AsyncSession = None
    ) -> models.User:
        if isinstance(create_user_data, schemas.UserCreateDataSchema):
            create_user_data = create_user_data.model_dump()
        create_user_data['password'] = crypt_context.hash(create_user_data['password'])
        return await self.create(create_user_data, session=session)

    async def authenticate(
        self, data: OAuth2PasswordRequestForm, session: AsyncSession = None
    ) -> models.User | None:
        stmt = self.get_query().where(models.User.email == data.username)
        user: models.User = await self.select_one(stmt, session=session)
        if not user:
            return None
        if not self.verify_password(user, data.password):
            return None
        return user

    def verify_password(self, user: models.User, password: str) -> bool:
        return crypt_context.verify(password, user.password)

    def validate_token(self, token: str) -> dict:
        try:
            payload = decode(
                token,
                config.secret_key.get_secret_value(),
                algorithms=[config.jwt_hashing_algorithm],
            )
            return payload
        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Token expired')
        except InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token')

    def make_user_tokens(self, user: models.User) -> schemas.Tokens:
        secret_key = config.secret_key.get_secret_value()
        access_token_data = user.model_dump(mode='json', exclude={'password'})
        access_expires = datetime.now(UTC) + timedelta(minutes=config.access_token_expire)
        access_token_data['exp'] = utils.to_unix_timestamp(access_expires.timestamp())
        access = encode(access_token_data, secret_key, algorithm=config.jwt_hashing_algorithm)
        refresh_token_data = user.model_dump(mode='json', exclude={'email', 'password'})
        refresh_expires = datetime.now(UTC) + timedelta(days=config.refresh_token_expire)
        refresh_token_data['exp'] = utils.to_unix_timestamp(refresh_expires.timestamp())
        refresh = encode(refresh_token_data, secret_key, algorithm=config.jwt_hashing_algorithm)
        return schemas.Tokens(access_token=access, refresh_token=refresh)
