from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from minager.core.settings.amqp import AMQPConfig
from minager.core.settings.db import DBConnectionConfig
from minager.core.settings.logging import LoggingConfig
from minager.surorm.settings import SurrealConfig


class ApplicationConfig(BaseSettings):
    debug: bool = False
    logging: LoggingConfig = LoggingConfig()
    palace_node_db: SurrealConfig
    learning_session_db: DBConnectionConfig
    main_db: DBConnectionConfig
    user_events_routing_key: str
    user_events: AMQPConfig

    base_path: str = str(Path(__file__).parent)

    model_config = SettingsConfigDict(env_nested_delimiter='__', env_file=('.env.local', '.env'))


config = ApplicationConfig()
user_profile_db_engine = create_async_engine(config.main_db.to_str(), echo=True)
user_profile_db = async_sessionmaker(user_profile_db_engine, expire_on_commit=False)

main_db_engine = create_async_engine(config.main_db.to_str(), echo=True)
main_db = async_sessionmaker(main_db_engine, expire_on_commit=False)
