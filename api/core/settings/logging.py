from logging import INFO

from pydantic_settings import BaseSettings


class LoggingConfig(BaseSettings):

    level: int = INFO
    format: str = '%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s'
    # datetime_format: str = ''

    def to_basic_config(self) -> dict:
        return {
            'level': self.level,
            'format': self.format,
            # 'datefmt': self.datetime_format
        }
