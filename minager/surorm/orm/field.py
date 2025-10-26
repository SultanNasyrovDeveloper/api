from typing import Type

from pydantic import Field as BaseField
from pydantic.fields import FieldInfo

from ..base import DataType


def Field(type_: Type[DataType], *args, **kwargs) -> FieldInfo:
    user_json_schema_extra = kwargs.pop('json_schema_extra', {})
    json_schema_extra = {
        **user_json_schema_extra,
        'surreal_type': type_.name,
    }

    return BaseField(*args, json_schema_extra=json_schema_extra, **kwargs)
