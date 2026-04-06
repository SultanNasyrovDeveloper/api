from datetime import datetime
from decimal import Decimal
from typing import Any, ClassVar

from minager.core.surorm import data_model
from minager.core.surorm.orm.field import Field
from minager.core.surorm.orm.models import Model


class DummyModel(Model):
    __table_name__: ClassVar[str] = 'dummy_table_name'

    # Record types
    record_field: str = Field(data_model.Record)
    record_id_field: dict = Field(data_model.Record)

    # Primitive types
    null_field: None = Field(data_model.Null)
    bool_field: bool = Field(data_model.Boolean)
    number_int: int = Field(data_model.Number)
    number_float: float = Field(data_model.Number)
    number_decimal: Decimal = Field(data_model.Number)
    string_field: str = Field(data_model.String)

    # Complex types
    datetime_field: datetime = Field(data_model.Datetime)
    json_field: dict = Field(data_model.Json)

    # Collections
    array_field: list[Any] = Field(data_model.Array)
    sequence_field: list[Any] = Field(data_model.Sequence)
