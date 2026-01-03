from datetime import datetime

from minager.core.surorm import data_model
from minager.core.surorm.orm.field import Field
from minager.core.surorm.orm.models import Model


class Node(Model):
    __tablename__ = 'knowledge_tree.node'

    is_learn: bool = Field(data_model.Boolean)
    title: str = Field(data_model.String)
    order: str = Field(data_model.String)
    owner_id: str = Field(data_model.String)
    questions: str = Field(data_model.String)

    cpr: int = Field(data_model.Number, default=0)
    owner_views: int = Field(data_model.Number, default=0)
    difficulty: float = Field(data_model.Number, default=2.6)
    last_rating: float = Field(data_model.Number, default=0)
    size: int = Field(data_model.Number, default=0)
    repetitions: int = Field(data_model.Number, default=0)

    last_interval: int = Field(data_model.Number)
    last_repetition: datetime = Field(data_model.Datetime)
    next_optimal_repetition: datetime = Field(data_model.Datetime)

    content: dict = Field(data_model.Json)
