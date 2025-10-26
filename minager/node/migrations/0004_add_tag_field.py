from minager.surorm import DefineField, Remove
from minager.surorm.migrations import MigrationOperation

operations = [
    MigrationOperation(query=Remove('field', 'tags').on('table', 'node').if_exists(True)),
    MigrationOperation(
        query=DefineField('tags', 'array<int>').on('node').if_not_exists(True).default('[]')
    ),
]
