from asyncio import get_running_loop
from typing import Annotated, Any

from bson import ObjectId
from pydantic import AfterValidator, PlainSerializer, WithJsonSchema
from pymongo import AsyncMongoClient

from ..settings.db import DBConnectionConfig


def validate_object_id(v: Any) -> ObjectId:
    if isinstance(v, ObjectId):
        return v
    if ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError('Invalid ObjectId')


MongoDBId = Annotated[
    str | ObjectId,
    AfterValidator(validate_object_id),
    PlainSerializer(lambda x: str(x), return_type=str),
    WithJsonSchema({'type': 'string'}, mode='serialization'),
]


class MongoDBManager[ModelT]:
    collection: str
    model_class: ModelT

    def __init__(self, config: DBConnectionConfig):
        assert self.collection
        self._config = config
        self.client = AsyncMongoClient(self._config.to_str(scheme='mongodb'))
        self.client.get_io_loop = get_running_loop
        self.connection = self.client[self._config.name][self.collection]

    async def create(self, data: dict) -> ModelT:
        response = await self.connection.insert_one(data)
        new_item = await self.connection.find_one({'_id': response.inserted_id})
        return self.model_class.model_validate(new_item)
