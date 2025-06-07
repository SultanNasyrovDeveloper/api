import logging

from api.settings import config

logging.basicConfig(**config.logging.to_basic_config())
logging.getLogger('websockets').setLevel(logging.DEBUG)


def get_logger(name: str, service: str = 'Minager') -> logging.Logger:
    return logging.getLogger(name)
