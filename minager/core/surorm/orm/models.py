from pydantic import BaseModel


class Table(BaseModel):
    pass


class Model(Table):
    pass


class Relation(Table):
    pass
