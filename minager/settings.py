from pathlib import Path

from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from minager.core.settings import SMTPServerConfiguration
from minager.core.settings.amqp import AMQPConfig
from minager.core.settings.db import DBConnectionConfig
from minager.core.settings.logging import LoggingConfig
from minager.core.surorm.core.settings import SurrealConfig


class ApplicationConfig(BaseSettings):
    debug: bool = False
    base_path: str = str(Path(__file__).parent)

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
    user_events_routing_key: str
    user_events: AMQPConfig

    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file=('.env.local', '.env'))


config = ApplicationConfig()

main_db_engine = create_async_engine(config.main_db.to_str(), echo=True)
main_db = async_sessionmaker(main_db_engine, expire_on_commit=False)

user_profile_db_engine = create_async_engine(config.main_db.to_str(), echo=True)
user_profile_db = async_sessionmaker(user_profile_db_engine, expire_on_commit=False)

crypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
AuthBearerToken = OAuth2PasswordBearer(tokenUrl='/api/v1/auth/users/token')
