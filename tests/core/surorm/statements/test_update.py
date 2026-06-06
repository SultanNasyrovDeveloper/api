from faker import Faker

from minager.core import surorm

from .models import DummyModel


def test_update_set_basic(faker: Faker):
    data = {'bool_field': True, 'number_int': faker.pyint(), 'number_float': faker.pyfloat()}
    stmt = surorm.Update(surorm.Record(DummyModel, faker.pystr())).set(**data)
    sql = stmt.sql()
    assert sql.startswith(f'update {DummyModel.__table_name__}')
    assert 'set' in sql
    assert 'bool_field = true' in sql
    assert f'number_int = {data["number_int"]}' in sql
    assert f'number_float = {data["number_float"]}' in sql
