from abc import ABCMeta, abstractmethod
from typing import Any

from surrealdb import RecordID

from .. import data_model
from .models import Model

SURREAL_TYPE_MAP = {
    'boolean': data_model.Boolean,
    'number': data_model.Number,
    'string': data_model.String,
    'datetime': data_model.Datetime,
    'array': data_model.Array,
    'sequence': data_model.Sequence,
    'json': data_model.Json,
    'object': data_model.Object,
    'record': RecordID,
}


class BaseSerializer(metaclass=ABCMeta):
    model: Model

    @abstractmethod
    def serialize(self, data: dict, mode: str):
        pass


class Serializer(BaseSerializer):
    """
    This class allows to serialize any python dict into surreal query language compatible
    string based on model class defined.
    """

    def serialize(self, data: dict, mode: str = 'content') -> str:
        serialized_object: dict[str, str] = {}
        for field_name, value in data.items():
            serialized_value = self.serialize_field(field_name, value)
            if serialized_value:
                serialized_object[field_name] = serialized_value
        if mode == 'set':
            return str(
                ', '.join(
                    [f'{field_name} = {value}' for field_name, value in serialized_object.items()]
                )
            )
        return f'{{{', '.join([f'{field_name}: {value}' for field_name, value in serialized_object.items()])}}}'

    def serialize_field(self, name: str, value: Any) -> str | None:
        field_metadata = self.model.model_fields.get(name, None)
        if not field_metadata:
            return None
        surreal_type_name = field_metadata.json_schema_extra.get('surreal_type', None)
        if not surreal_type_name or surreal_type_name not in SURREAL_TYPE_MAP:
            return None
        surreal_type = SURREAL_TYPE_MAP[surreal_type_name]
        return str(surreal_type(value))
