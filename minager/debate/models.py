from minager.core.db.mixins import IdentifierMixin
from minager.core.db.models import Field, Model


class Debate(Model, IdentifierMixin):
    __tablename__ = 'debate__debates'

    duration = None


class DebateMove(Model, IdentifierMixin):
    __tablename__ = 'debate__debate_messages'

    debate: int = Field(foreign_key='')
    content: str = Field()
