from typing import Any

from pydantic import BaseModel

from .query import data_model

SURREAL_PRIMARY_MAP = {
    data_model.Null: lambda field: field.get('type') == 'null',
    data_model.Boolean: lambda field: field.get('type') == 'boolean',
    data_model.Number: lambda field: field.get('type') in ('integer', 'number'),
    data_model.String: lambda field: field.get('type') == 'string' and field.get('format') is None,
    data_model.Datetime: lambda field: field.get('type') == 'string'
    and field.get('format') == 'date-time',
    data_model.Json: lambda field: field.get('type') == 'string' and field.get('format') == 'json',
}


def is_optional(schema: dict):
    types = schema.get('anyOf', [])
    length = len(types)
    if length != 2:
        return False
    return any([type_schema.get('type') == 'null' for type_schema in schema.get('anyOf', [])])


def get_optional_type_schema(schema: dict):
    target = list(map(lambda type_schema: type_schema.get('type') != 'null', schema))
    return target[0]


def get_array_item_schema(field_schema: dict):
    items = field_schema.get('items')
    item_schema = items[0] if isinstance(items, list) else items
    array_field_schema = {key: value for key, value in field_schema.items() if key not in ('type',)}
    return {**array_field_schema, **item_schema}


class SurrealSerializer(BaseModel):

    def model_dump_surreal(self, **kwargs):
        schema = self.model_json_schema()
        field_types = schema.get('properties')
        data = self.model_dump(**kwargs)
        output = []
        for key, value in data.items():
            field_schema = field_types.get(key)
            if not field_schema:
                continue
            surreal_value = self.serialize_field(value, field_schema)
            output.append(f'{key}: {surreal_value.sql()}')
        return f'{{{', '.join(output)}}}'

    def serialize_field(self, value: Any, schema: dict) -> data_model.Expression:
        schema = dict(schema)
        if 'anyOf' in schema:
            if is_optional(schema):
                if value is None:
                    return str(data_model.Null())
                else:
                    type_schema = get_optional_type_schema(schema)
                    schema.update(type_schema)
            else:
                items = schema.get('anyOf')
                schema.update(items[0])

        if '$ref' in schema:
            # handle object field
            pass
        if schema.get('type') == 'object':
            pass
        if schema.get('type') == 'array':
            items = [self.serialize_field(item, get_array_item_schema(schema)) for item in value]
            return data_model.Array(*items)
        if schema.get('type') == 'string' and schema.get('table') is not None:
            return data_model.Record(schema.get('table'), value)
        if schema.get('type') in ('null', 'boolean', 'integer', 'number', 'string'):
            for primitive_type_class, check_type in SURREAL_PRIMARY_MAP.items():
                if check_type(schema):
                    return primitive_type_class(value)
