from api.surorm.migrations import MigrationOperation
from api.surorm.query import DefineField, Remove


operations = [
    MigrationOperation(query=Remove('field', 'tags').on('table', 'node').if_exists(True)),
    MigrationOperation(query=DefineField('tags', 'array<int>').on('node').if_not_exists(True).default('[]'))
]
