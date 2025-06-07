from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.core.settings.amqp import AMQPConfig
from api.core.settings.db import DBConnectionConfig
from api.core.settings.logging import LoggingConfig
from api.surorm.settings import SurrealConfig


class ApplicationConfig(BaseSettings):
    debug: bool = False
    logging: LoggingConfig = LoggingConfig()
    palace_node_db: SurrealConfig
    user_profile_db: DBConnectionConfig
    learning_session_db: DBConnectionConfig
    user_events_routing_key: str
    user_events: AMQPConfig

    base_path: str = str(Path(__file__).parent)

    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file=('.env.local', '.env'))


config = ApplicationConfig()
user_profile_db_engine = create_async_engine(config.user_profile_db.to_str(), echo=True)
user_profile_db = async_sessionmaker(user_profile_db_engine, expire_on_commit=False)
