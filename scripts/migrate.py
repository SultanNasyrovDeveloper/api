import argparse
import asyncio

from minager.app import config
from minager.logger import get_logger
from minager.surorm.manager import SurrealDBManager
from minager.surorm.migrations import PerformMigrationCommand

logger = get_logger(__name__)


async def migrate():
    parser = argparse.ArgumentParser(description='Perform surreal database migrations.')
    parser.add_argument('operation', type=str, default='upgrade')
    parser.add_argument('--app', type=str, required=False, default=None)
    parser.add_argument('--number', type=str, required=False, default=None)
    arguments = parser.parse_args()
    client = SurrealDBManager(config=config.palace_node_db)
    async with client as session:
        command = PerformMigrationCommand(session, config.base_path)
        if arguments.operation == 'upgrade':
            await command.upgrade(app=arguments.app, migration_number=arguments.number)


def run():
    asyncio.run(migrate())


if __name__ == '__main__':
    run()
