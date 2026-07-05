from uuid import UUID

from pydantic import BaseModel


class TokenPayloadSchema(BaseModel):
    """Decoded JWT token payload"""

    sub: UUID  # Subject (user ID)
    exp: int  # Expiration timestamp
    iat: int  # Issued at timestamp
    type: str  # Token type: 'access' or 'refresh'


class AccessTokenSchema(BaseModel):
    """Access token response"""

    access_token: str
    token_type: str = 'bearer'


class TokenPairSchema(BaseModel):
    """Access + Refresh token pair response"""

    token_type: str = 'bearer'
    access_token: str
    refresh_token: str


class RefreshTokenRequestSchema(BaseModel):
    """Request to refresh access token"""

    refresh_token: str
