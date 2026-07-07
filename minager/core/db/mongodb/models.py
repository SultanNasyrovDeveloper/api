from pydantic import BaseModel, ConfigDict, Field

from .fields import MongoDBId


class MongoDBModel(BaseModel):
    """
    Base model for MongoDB documents with common configuration.
    """

    id: MongoDBId | None = Field(alias='_id', default=None)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True,
        from_attributes=True,
    )
