from datetime import UTC, datetime

from faker import Faker

from minager.core.surorm.constants import DATETIME_FORMAT

from .conftest import TestModelSerializer

serializer = TestModelSerializer()


def test_serialize_boolean_field():
    serialized_value = serializer.serialize_field('boolean_field', True)
    assert serialized_value == 'true'

    serialized_value = serializer.serialize_field('boolean_field', False)
    assert serialized_value == 'false'


def test_serialize_number_field(faker: Faker):
    integer = faker.pyint()
    serialized_integer = serializer.serialize_field('number_field', integer)
    assert serialized_integer == str(integer)

    float_number = faker.pyfloat()
    serialized_float = serializer.serialize_field('number_field', float_number)
    assert serialized_float == str(float_number)

    decimal = faker.pydecimal()
    serialized_decimal = serializer.serialize_field('number_field', decimal)
    assert serialized_decimal == f'{str(decimal)}dec'


def test_serialize_datetime_field(faker: Faker):
    initial_value = datetime.now(UTC)
    serialized_value = serializer.serialize_field('datetime_field', initial_value)
    assert serialized_value == f'd"{initial_value.strftime(DATETIME_FORMAT)}"'


def test_serializer_record_id_field():
    pass
