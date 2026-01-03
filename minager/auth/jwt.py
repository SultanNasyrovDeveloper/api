from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID

import jwt
from fastapi import HTTPException, status
from jwt.exceptions import InvalidTokenError

from minager.auth import schemas
from minager.settings import ApplicationConfig, config


class JWTService:
    """Service for handling JWT token operations"""

    def __init__(
        self,
        secret: str,
        algorithm: str = 'HS256',
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days=7,
    ):
        self.secret_key = secret
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    @classmethod
    def from_config(cls, configuration: ApplicationConfig = config) -> Self:
        return cls(
            secret=configuration.secret_key.get_secret_value(),
            algorithm=configuration.jwt_hashing_algorithm,
            access_token_expire_minutes=configuration.access_token_expire,
            refresh_token_expire_days=configuration.refresh_token_expire,
        )

    def create_access_token(self, user_id: UUID) -> str:
        """Create JWT access token"""
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            'sub': str(user_id),
            'exp': int(expire.timestamp()),
            'iat': int(now.timestamp()),
            'type': 'access',
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: UUID) -> str:
        """Create JWT refresh token"""
        now = datetime.now(UTC)
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            'sub': str(user_id),
            'exp': int(expire.timestamp()),
            'iat': int(now.timestamp()),
            'type': 'refresh',
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_token_pair(self, user_id: UUID) -> schemas.TokenPairSchema:
        """Create both access and refresh tokens"""
        return schemas.TokenPairSchema(
            access_token=self.create_access_token(user_id),
            refresh_token=self.create_refresh_token(user_id),
        )

    def decode_token(self, token: str) -> schemas.TokenPayloadSchema:
        """
        Decode and validate JWT token.
        Raises HTTPException if token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={'verify_exp': True, 'verify_iat': True},
            )
            return schemas.TokenPayloadSchema(
                sub=UUID(payload['sub']),
                exp=payload['exp'],
                iat=payload['iat'],
                type=payload['type'],
            )
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Could not validate credentials',
                headers={'WWW-Authenticate': 'Bearer'},
            ) from e

    def verify_token_type(self, token: str, expected_type: str) -> schemas.TokenPayloadSchema:
        """
        Verify token is of expected type (access or refresh).
        Raises HTTPException if type doesn't match.
        """
        payload = self.decode_token(token)

        if payload.type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f'Invalid token type. Expected {expected_type}, got {payload.type}',
                headers={'WWW-Authenticate': 'Bearer'},
            )

        return payload

    def refresh_access_token(self, refresh_token: str) -> schemas.AccessTokenSchema:
        """
        Create new access token from valid refresh token.
        Validates that provided token is a refresh token.
        """
        payload = self.verify_token_type(refresh_token, 'refresh')
        new_access_token = self.create_access_token(payload.sub)

        return schemas.AccessTokenSchema(access_token=new_access_token)


# Global JWT service instance
jwt_service = JWTService.from_config()
