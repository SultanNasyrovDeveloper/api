from typing import Any, Callable, ClassVar, Dict, Type

from pydantic import BaseModel, ConfigDict
from sqlalchemy.sql import operators
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


class FilterSetConfiguration(ConfigDict):
    model: Type[SQLModel]


class FilterSet(BaseModel):
    configuration: ClassVar[FilterSetConfiguration] = None

    def get_filters(self) -> list:
        expressions = []
        if not self.configuration:
            return []
        model = self.configuration['model']
        for field_name, field_def in self.model_fields.items():
            value = getattr(self, field_name, None)
            if value is None:
                continue

            # Use custom method if defined
            if method_name := field_def.json_schema_extra.get('method', None):
                method = getattr(self, method_name, None)
                if not callable(method):
                    raise ValueError(f"Custom method '{method_name}' is not defined or callable")
                expr = method(value)
                if expr is not None:
                    expressions.append(expr)
                continue

            # Default behavior using lookups
            model_column = getattr(model, field_name, None)
            if model_column is None:
                raise ValueError(
                    f"Field '{field_name}' does not exist on model " f"'{model.__name__}'"
                )

            lookup = field_def.json_schema_extra.get('lookup', 'exact')
            if lookup not in LOOKUP_MAP:
                raise ValueError(f"Unsupported lookup type: '{lookup}'")

            operator = LOOKUP_MAP[lookup]
            expressions.append(operator(model_column, value))

        return expressions
