from sqlmodel import Field, SQLModel  # noqa

from minager.logger import get_logger

logger = get_logger(__name__)


class Model(SQLModel):
    def update(self, data: dict) -> None:
        validated_update_data = self.model_copy(update=data)
        for key, value in data.items():
            if key in self.model_fields:
                setattr(self, key, getattr(validated_update_data, key))
            else:
                # TODO: Handle this correctly
                logger.warning(
                    f'{self.__class__.__name__} has no field {key}. '
                    f'Available fields: {', '.join(self.model_fields.keys())}'
                )
