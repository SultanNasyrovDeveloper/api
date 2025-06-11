from time import sleep

from requests import request

from .settings import SurrealConfig


class SurrealConnectionTester:

    MAX_RETRIES = 10
    RETRIES_SLEEP = 10

    def __init__(self, config: SurrealConfig):
        assert config.driver == 'surreal'
        self.config = config

    def test(self) -> bool:
        # logger.info(f'Testing surreal db connection at {self.config.host}:{self.config.port}...')
        url = f'http://{self.config.host}:{self.config.port}/health'
        try:
            response = request('get', url)
        except ConnectionError:
            return False
        return response.status_code == 200

    def wait(self) -> bool:
        is_connected = False
        retries = 0
        while not is_connected and retries < self.MAX_RETRIES:
            try:
                is_connected = self.test()
            except Exception:
                pass
                # logger.warning(
                #     f'Unusual exception occured when trying to connect to surrealdb: {str(e)}.'
                # )
            if not is_connected:
                # logger.info(f'Unable to connect to surrealdb. Waiting {self.RETRIES_SLEEP} sec...')
                retries += 1
                sleep(self.RETRIES_SLEEP)
        if is_connected:
            pass
            # logger.info('Surreal db connection is available.')
        return is_connected
