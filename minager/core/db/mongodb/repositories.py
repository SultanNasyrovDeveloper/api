from bson import ObjectId
from motor import motor_asyncio as motor
from pymongo import ReturnDocument

from .models import MongoDBModel


class MongoDBRepository[ModelT: MongoDBModel]:
    COLLECTION: str
    model_class: type[ModelT]

    def __init__(self, connection: motor.AsyncIOMotorCollection):
        self.connection = connection

    async def get(self, id_: str | ObjectId) -> ModelT | None:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        session_data = await self.connection.find_one({'_id': id_})
        return self.model_class.model_validate(session_data) if session_data else None

    async def create(self, data: dict) -> ModelT | None:
        insert_result = await self.connection.insert_one(data)
        return await self.get(insert_result.inserted_id)

    async def update(self, id_: str | ObjectId, data: dict) -> ModelT:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        updated = await self.connection.find_one_and_update(
            {'_id': id_}, {'$set': data}, return_document=ReturnDocument.AFTER
        )
        if updated is None:
            raise ValueError(f'LearningSession({id_}) not found')
        return self.model_class.model_validate(updated)
