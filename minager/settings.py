from pathlib import Path

from fastapi.security import OAuth2PasswordBearer
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from minager.core.settings import SMTPServerConfiguration
from minager.core.settings.db import DBConnectionConfig
from minager.core.settings.logging import LoggingConfig
from minager.core.surorm.core.settings import SurrealConfig


class ApplicationConfig(BaseSettings):
    debug: bool = False
    base_path: str = str(Path(__file__).parent)
    huggingface_api_token: str | None = Field(default=None)
    huggingface_llm_model: str = 'meta-llama/Llama-3.1-8B-Instruct'

    # Security
    jwt_hashing_algorithm: str = 'HS256'
    secret_key: SecretStr
    access_token_expire: int = 60  # minutes
    refresh_token_expire: int = 7  # days

    # SMTP
    smtp: SMTPServerConfiguration | None = None

    logging: LoggingConfig = LoggingConfig()

    # Databases
    main_db: DBConnectionConfig
    palace_node_db: SurrealConfig
    learning_session_db: DBConnectionConfig

    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file=('.env.local', '.env'))


config = ApplicationConfig()

main_db_engine = create_async_engine(config.main_db.to_str(), echo=True)
main_db = async_sessionmaker(main_db_engine, expire_on_commit=False)

crypt_context = PasswordHash((BcryptHasher(),))
AuthBearerToken = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/users/token')
