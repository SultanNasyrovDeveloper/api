from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from surorm.settings import SurrealConfig

from api.core.settings.amqp import AMQPConfig
from api.core.settings.logging import LoggingConfig


class ApplicationConfig(BaseSettings):
    debug: bool = False
    logging: LoggingConfig = LoggingConfig()
    palace_node_db: SurrealConfig
    user_events_routing_key: str
    user_events: AMQPConfig

    base_path: str = str(Path(__file__).parent)

    model_config = SettingsConfigDict(env_nested_delimiter='__')


config = ApplicationConfig()
