from yarl import URL

from minager.core.settings.db import DBConnectionConfig


def make_database_url(config: DBConnectionConfig, **additional) -> str:
    url = URL.build(
        user=config.username,
        password=config.password.get_secret_value(),
        host=config.host or '',
        port=config.port,
        **additional,
    )
    return str(url)
