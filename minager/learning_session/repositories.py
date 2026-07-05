from bson import ObjectId
from motor import motor_asyncio as motor
from pymongo import ReturnDocument

from .models import LearningSession


class LearningSessionRepository:
    COLLECTION = 'session'

    def __init__(self, connection: motor.AsyncIOMotorCollection):
        self.connection = connection

    async def get(self, id_: str | ObjectId) -> LearningSession | None:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        session_data = await self.connection.find_one({'_id': id_})
        return LearningSession.model_validate(session_data) if session_data else None

    async def find_active_for_user(self, user_id: str) -> LearningSession | None:
        session_data = await self.connection.find_one({'user_id': user_id, 'is_active': True})
        return LearningSession.model_validate(session_data) if session_data else None

    async def create(self, data: dict | LearningSession) -> LearningSession:
        document = data.model_dump(mode='json') if isinstance(data, LearningSession) else data
        insert_result = await self.connection.insert_one(document)
        return await self.get(insert_result.inserted_id)

    async def update(self, id_: str | ObjectId, data: dict) -> LearningSession:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        updated = await self.connection.find_one_and_update(
            {'_id': id_}, {'$set': data}, return_document=ReturnDocument.AFTER
        )
        if updated is None:
            raise ValueError(f'LearningSession({id_}) not found')
        return LearningSession.model_validate(updated)
