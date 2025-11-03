from typing import Any, Callable, ClassVar, Dict, Type, TypedDict

from pydantic import BaseModel
from pydantic import Field as PydanticField
from sqlalchemy.sql import operators
from sqlalchemy.sql.expression import ColumnElement
from sqlmodel import SQLModel

LOOKUP_MAP: Dict[str, Callable[[Any, Any], Any]] = {
    'exact': operators.eq,
    'gt': operators.gt,
    'gte': operators.ge,
    'lt': operators.lt,
    'lte': operators.le,
    'contains': lambda field, value: field.contains(value),
    'icontains': lambda field, value: field.ilike(f"%{value}%"),
    'in': lambda field, value: field.in_(value if isinstance(value, list) else [value]),
}


def Field(
    field_name: str | None = None,
    method: str | None = None,
    lookup: str | None = None,
    json_schema_extra: dict | None = None,
    **kwargs,
) -> PydanticField:
    json_schema = json_schema_extra or {}
    if field_name:
        json_schema['field_name'] = field_name
    if method:
        json_schema['method'] = method
    if lookup:
        json_schema['lookup'] = lookup
    return PydanticField(json_schema_extra=json_schema, **kwargs)


class FilterSetConfiguration(TypedDict):
    model: Type[SQLModel]


class FilterSet(BaseModel):
    configuration: ClassVar[FilterSetConfiguration] = None

    def get_filters(self) -> list[ColumnElement[bool]]:
        data = self.model_dump(exclude_unset=True)
        expressions = []
        if not self.configuration:
            raise ValueError(
                f"{self.__class__.__name__} must define a 'configuration' ClassVar "
                f"with a 'model' key pointing to a SQLModel class"
            )
            return []
        model = self.configuration['model']
        for field_name, field_def in self.model_fields.items():
            if field_name not in data:
                continue
            value = data.get(field_name)

            # Use custom method if defined
            if method_name := field_def.json_schema_extra.get('method', None):
                method = getattr(self, method_name, None)
                if not callable(method):
                    raise ValueError(f"Custom method '{method_name}' is not defined or callable")
                expr = method(value)
                if expr is not None:
                    if isinstance(expressions, (tuple, list)):
                        expressions.extend(list(expr))
                    else:
                        expressions.append(expr)
                continue

            # Default behavior using lookups
            model_field_name = field_def.json_schema_extra.get('field_name', field_name)
            model_column = getattr(model, model_field_name, None)
            if model_column is None:
                raise ValueError(
                    f"Field '{model_field_name}' does not exist on model " f"'{model.__name__}'"
                )

            lookup = field_def.json_schema_extra.get('lookup', 'exact')
            if lookup not in LOOKUP_MAP:
                raise ValueError(f"Unsupported lookup type: '{lookup}'")

            operator = LOOKUP_MAP[lookup]
            expressions.append(operator(model_column, value))

        return expressions
