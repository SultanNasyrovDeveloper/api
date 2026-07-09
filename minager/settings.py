from asyncio import get_running_loop
from pathlib import Path

from motor import motor_asyncio as motor
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from surorm.core.settings import SurrealConfig
from surrealdb import AsyncSurreal

from minager.core.settings import SMTPServerConfiguration
from minager.core.settings.cors import CorsConfiguration
from minager.core.settings.db import DBConnectionConfig
from minager.core.settings.logging import LoggingConfig


class ApplicationConfig(BaseSettings):
    debug: bool = False
    base_path: str = str(Path(__file__).parent)
    cors: CorsConfiguration

    # AI
    huggingface_api_token: str | None = Field(default=None)
    huggingface_llm_model: str = 'meta-llama/Llama-3.1-8B-Instruct'

    openai_api_token: str
    openai_chat_model: str
    openai_speech_to_text_model: str | None = Field(default=None)

    # Security
    jwt_hashing_algorithm: str = 'HS256'
    secret_key: SecretStr
    access_token_expire: int = 60  # minutes
    refresh_token_expire: int = 7  # days

    # SMTP
    smtp: SMTPServerConfiguration | None = None

    logging: LoggingConfig = LoggingConfig()

    # Databases
    postgres: DBConnectionConfig
    surreal: SurrealConfig
    mongo: DBConnectionConfig

    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file=('.env.local', '.env'))


config = ApplicationConfig()

postgres_engine = create_async_engine(config.postgres.to_str(), echo=config.debug)
postgres_connection_factory = async_sessionmaker(postgres_engine, expire_on_commit=False, autoflush=True)

mongo = motor.AsyncIOMotorClient(config.mongo.to_str(scheme='mongodb'))
mongo.get_io_loop = get_running_loop
surreal = AsyncSurreal(f'ws://{config.surreal.host}:{config.surreal.port}')

password_hash = PasswordHash((BcryptHasher(),))
