import asyncio
import json

import aio_pika
from aio_pika.exchange import ExchangeType

from api.core.amqp.tester import AsyncAMQPConnectionTester
from api.logger import get_logger
from api.node.managers import PalaceNodeManager
from api.settings import config, user_profile_db
from api.user_profile.models import UserProfile

logger = get_logger(__name__)
nodes_manager = PalaceNodeManager(config.palace_node_db)


async def handler(message: aio_pika.abc.AbstractIncomingMessage):
    async with message.process():
        body = json.loads(message.body)
        if body['type'] in ('SEND_VERIFY_EMAIL', 'SEND_VERIFY_EMAIL_ERROR'):
            logger.info('new message recieved')
            logger.info(body)
            user_id = body['userId']
            async with nodes_manager:
                user_palace_root = await nodes_manager.get_my_palace_root(user_id)
                if not user_palace_root:
                    new_ = await nodes_manager.create(
                        owner_id=user_id,
                        title='Mind Palace',
                        questions='What is Mind Palace?',
                    )
                    logger.info(new_)
            new_user = UserProfile(user_id=user_id)
            async with user_profile_db.begin() as session:
                session.add(new_user)
            logger.info(f'New user created: ID={body['userId']}...')


async def main():
    connection = await aio_pika.connect_robust(config.user_events.url())
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            name=config.user_events.exchange,
            type=ExchangeType.TOPIC,
            passive=False,
            durable=True,
            auto_delete=False,
        )
        queue = await channel.declare_queue('client_user_events')
        await queue.bind(exchange, routing_key=config.user_events_routing_key)
        await queue.consume(handler)

        logger.info('[*] Waiting for logs. To exit press CTRL+C')
        try:
            await asyncio.Future()
        finally:
            await connection.close()


if __name__ == '__main__':
    tester = AsyncAMQPConnectionTester(config.user_events)
    loop = asyncio.new_event_loop()
    is_connected = loop.run_until_complete(tester.wait())
    if not is_connected:
        raise ConnectionError('Not Connected')
    logger.info('Starting main...')
    asyncio.run(main())
