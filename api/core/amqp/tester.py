from time import sleep

from aio_pika import connect
from aiormq.exceptions import AMQPConnectionError
from requests.exceptions import ConnectionError

from api.core.settings.amqp import AMQPConfig
from api.logger import get_logger

logger = get_logger(__name__)


class AsyncAMQPConnectionTester:
    def __init__(self, config: AMQPConfig) -> None:
        self._config = config

    def check(self) -> bool:
        pass

    async def wait(self) -> bool:
        logger.info(f'Starting amqp connection testing for {self._config.host}:{self._config.port}')
        is_connected = False
        retries = 0
        connection = None
        while not is_connected and retries < 10:
            try:
                logger.info('Testing connection...')
                logger.info(self._config.url())
                connection = await connect(self._config.url())
                is_connected = True
                logger.info('Sucessfully connected.')
            except (AMQPConnectionError, ConnectionError) as e:
                retries += 1
                if connection:
                    await connection.close()
                logger.info(str(e))
                logger.info('Not connected. Sleeping...')
                sleep(5)
            except Exception as e:
                logger.error('Unexpected error while trying to connect to amqp server.')
                logger.error(str(e))
                if connection:
                    await connection.close()
                retries += 1
                sleep(5)
        if connection:
            await connection.close()
        return is_connected
