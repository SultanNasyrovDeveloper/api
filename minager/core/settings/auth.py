from pydantic import AnyUrl, BaseModel, SecretStr


class KeycloakAuthConfig(BaseModel):
    server_url: AnyUrl
    realm: str
    client_id: str
    client_secret: SecretStr
