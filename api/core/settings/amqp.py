from pydantic import SecretStr
from pydantic_settings import BaseSettings
from yarl import URL


class AMQPConfig(BaseSettings):
    host: str = 'localhost'
    port: str = '5672'
    username: str
    password: SecretStr
    virtual_host: str = 'vhost'
    exchange: str

    def url(self) -> str:
        return str(
            URL.build(
                scheme='amqp',
                user=self.username,
                password=self.password.get_secret_value(),
                host=self.host,
                port=int(self.port),
                path='/' + self.virtual_host,
            )
        )
