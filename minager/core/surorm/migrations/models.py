from datetime import datetime

from .. import data_model
from ..orm.field import Field
from ..orm.models import Model


class Migration(Model):
    __table_name__ = 'migrations'

    app: str = Field(data_model.String)
    migration: str = Field(data_model.String)
    applied_at: datetime = Field(data_model.Datetime)
