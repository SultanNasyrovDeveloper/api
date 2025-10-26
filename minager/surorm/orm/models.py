from pydantic import BaseModel


class Table(BaseModel):
    tablename: str


class Model(Table):
    pass


class Relation(Table):
    pass
