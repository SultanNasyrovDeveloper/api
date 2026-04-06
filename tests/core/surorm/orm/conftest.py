from datetime import datetime
from typing import Any, ClassVar

from minager.core.surorm import data_model
from minager.core.surorm.orm.field import Field
from minager.core.surorm.orm.models import Model
from minager.core.surorm.orm.serializer import Serializer


class TestModel(Model):
    __table_name__: ClassVar[str] = 'node'

    # Primitive types
    null_field: None = Field(data_model.Null)
    boolean_field: bool = Field(data_model.Boolean)
    number_field: int = Field(data_model.Number)
    string_field: str = Field(data_model.String)

    # Complex types
    datetime_field: datetime = Field(data_model.Datetime)
    json_field: dict = Field(data_model.Json)

    # Record types
    record_field: str = Field(data_model.Record)
    record_id_field: dict = Field(data_model.Record)

    # Collections
    array_field: list[Any] = Field(data_model.Array)
    sequence_field: list[Any] = Field(data_model.Sequence)


class TestModelSerializer(Serializer):
    model = TestModel
