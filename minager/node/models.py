from datetime import datetime

from minager.surorm import data_model
from minager.surorm.orm import models


# noinspection PyTypeChecker
class Node(models.Model):
    is_learn: bool = models.Field(data_model.Boolean)
    title: str = models.Field(data_model.String)
    order: str = models.Field(data_model.String)
    owner_id: str = models.Field(data_model.String)
    questions: str = models.Field(data_model.String)

    cpr: int = models.Field(data_model.Number, default=0)
    owner_views: int = models.Field(data_model.Number, default=0)
    difficulty: float = models.Field(data_model.Number, default=2.6)
    last_rating: float = models.Field(data_model.Number, default=0)
    size: int = models.Field(data_model.Number, default=0)
    repetitions: int = models.Field(data_model.Number, default=0)

    last_interval: int = models.Field(data_model.Number)
    last_repetition: datetime = models.Field(data_model.Datetime)
    next_optimal_repetition: datetime = models.Field(data_model.Datetime)

    content: dict = models.Field(data_model.Json)
