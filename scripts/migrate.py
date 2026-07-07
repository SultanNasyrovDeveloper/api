import argparse
import asyncio

from surorm import Session
from surorm.migrations import PerformMigrationCommand
from surrealdb import AsyncSurreal

from minager.app import config
from minager.logger import get_logger

logger = get_logger(__name__)


async def migrate():
    parser = argparse.ArgumentParser(description='Perform surreal database migrations.')
    parser.add_argument('operation', type=str, default='upgrade')
    parser.add_argument('--app', type=str, required=False, default=None)
    parser.add_argument('--number', type=str, required=False, default=None)
    arguments = parser.parse_args()

    connection = AsyncSurreal(f'ws://{config.surreal.host}:{config.surreal.port}')
    await connection.connect()
    await connection.signin(
        {
            'username': config.surreal.username,
            'password': config.surreal.password.get_secret_value(),
        }
    )
    await connection.use(namespace=config.surreal.namespace, database=config.surreal.name)
    try:
        session = Session(connection=connection)
        command = PerformMigrationCommand(session, config.base_path)
        if arguments.operation == 'upgrade':
            await command.upgrade(app=arguments.app, migration_number=arguments.number)
        elif arguments.operation == 'downgrade':
            await command.downgrade(app=arguments.app, migration_number=arguments.number)
    finally:
        await connection.close()


def run():
    asyncio.run(migrate())


if __name__ == '__main__':
    run()
