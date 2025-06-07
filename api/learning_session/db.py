import asyncio
from datetime import UTC, datetime, timedelta
from typing import Optional

from bson import ObjectId
from motor import motor_asyncio as motor
from pymongo import ReturnDocument

from api.core.clients.palace.client import PalaceNodeServiceClient
from api.core.settings.db import DBConnectionConfig

from . import schemas
from .repetition.sm2 import SuperMemo2LearningStrategy
from .utils import shuffle

# TODO: Move to some factory method
learning_strategy = SuperMemo2LearningStrategy()


class LearningSessionClient:

    COLLECTION = 'session'

    def __init__(self, config: DBConnectionConfig, palace_client: PalaceNodeServiceClient):
        self._config = config
        self._url = config.to_str(scheme='mongodb')
        self.client = motor.AsyncIOMotorClient(self._url)
        self.client.get_io_loop = asyncio.get_running_loop
        self.palace_client = palace_client
        self.connection = self.client[self._config.name][self.COLLECTION]

    async def get_my_active_session(self, user_id: str) -> Optional[schemas.LearningSessionSchema]:
        session_data = await self.connection.find_one({'user_id': user_id, 'is_active': True})
        if not session_data:
            return None
        session = schemas.LearningSessionSchema(**session_data)
        is_expired = session.last_activity_datetime.replace(tzinfo=UTC) < datetime.now(
            tz=UTC
        ) - timedelta(hours=1)
        if is_expired:
            await self.finish(session.id)
            return None
        return session

    async def get(self, id_: str) -> schemas.LearningSessionSchema:
        id_ = ObjectId(id_) if type(id_) is str else id_
        target = await self.connection.find_one({'_id': id_})
        return schemas.LearningSessionSchema.model_validate(target)

    async def start(self, user_id: str, data: dict) -> schemas.LearningSessionSchema:
        already_started = await self.connection.find_one({'is_active': True, 'user_id': user_id})
        if already_started:
            session = schemas.LearningSessionSchema.model_validate(already_started)
            is_expired = session.last_activity_datetime.replace(tzinfo=UTC) < datetime.now(
                tz=UTC
            ) - timedelta(hours=1)
            if is_expired:
                await self.finish(session.id)
            else:
                return schemas.LearningSessionSchema.model_validate(session)
        target = data.get('target')
        repetition_queue = await self.palace_client.get_subtree_ids(target, 50)
        shuffled_repetition_queue = shuffle(repetition_queue)
        session_to_create = schemas.CreateLearningSessionSchema(
            **data,
            user_id=user_id,
            current_node=(
                shuffled_repetition_queue[0] if len(shuffled_repetition_queue) > 0 else None
            ),
            queue=(shuffled_repetition_queue[1:] if len(shuffled_repetition_queue) > 1 else []),
        )
        insert_result = await self.connection.insert_one(session_to_create.model_dump(mode='json'))
        new_session = await self.connection.find_one({'_id': insert_result.inserted_id})
        return schemas.LearningSessionSchema.model_validate(new_session)

    async def regenerate_queue(self, id_: str) -> schemas.LearningSessionSchema:
        session = await self.get(id_)
        repetition_queue = await self.palace_client.get_subtree_ids(session.target, 50)
        shuffled_repetition_queue = shuffle(repetition_queue)
        return await self.update(
            id_,
            {
                'current_node': (
                    shuffled_repetition_queue[0] if len(shuffled_repetition_queue) > 0 else None
                ),
                'queue': (
                    shuffled_repetition_queue[1:] if len(shuffled_repetition_queue) > 1 else []
                ),
            },
        )

    async def update(self, id_: str | ObjectId, data: dict) -> schemas.LearningSessionSchema:
        id_ = id_ if type(id_) is ObjectId else ObjectId(id_)
        new_session = await self.connection.find_one_and_update(
            {'_id': ObjectId(id_)}, {'$set': data}, return_document=ReturnDocument.AFTER
        )
        return schemas.LearningSessionSchema.model_validate(new_session)

    async def record_repetition(
        self, session_id: str, node_id: str, rating: int, user_id: str
    ) -> schemas.LearningSessionSchema:
        session = await self.get(session_id)
        repeated_node = await self.palace_client.get_node(node_id)
        # Check if node was repeated not long ago do not save another repetition
        study_result = learning_strategy.study_node(repeated_node, rating)
        await self.palace_client.update_node(
            node_id,
            {
                'last_repetition': datetime.now(UTC),
                'difficulty': study_result.difficulty,
                'last_interval': study_result.interval,
                'next_optimal_repetition': study_result.next_repetition,
                'repetitions': repeated_node.repetitions + 1,
                'cpr': repeated_node.cpr + 1 if rating >= 3 else 0,
            },
        )
        session_update_data = {'last_activity_datetime': datetime.now(UTC)}
        if repeated_node.id in session.queue:
            session.queue.remove(node_id)
        if node_id == session.current_node:
            if not session.queue and session.bad_repetition_queue:
                session_update_data['current_node'] = (
                    session.bad_repetition_queue[0]
                    if len(session.bad_repetition_queue) > 0
                    else None
                )
                session_update_data['queue'] = (
                    session.bad_repetition_queue[1:]
                    if len(session.bad_repetition_queue) > 1
                    else []
                )
                session_update_data['bad_repetition_queue'] = []
            else:
                session_update_data['current_node'] = (
                    session.queue[0] if len(session.queue) > 0 else None
                )
                session_update_data['queue'] = session.queue[1:] if len(session.queue) > 1 else []
        if rating < 3:
            session_update_data['bad_repetition_queue'] = [
                *session.bad_repetition_queue,
                node_id,
            ]
        return await self.update(session.id, session_update_data)

    async def finish(self, id_: str) -> schemas.LearningSessionSchema:
        id_ = ObjectId(id_) if type(id_) is not ObjectId else id_
        await self.connection.update_one(
            {'_id': id_},
            {
                '$set': {
                    'is_active': False,
                    'finish_datetime': datetime.now(),
                    'current_node': None,
                    'queue': [],
                }
            },
        )
        return await self.connection.find_one({'_id': id_})
