from minager.core.surorm import DefineField, Remove
from minager.core.surorm.migrations import MigrationOperation

operations = [
    MigrationOperation(query=Remove('field', 'tags').on('table', 'node').if_exists(True)),
    MigrationOperation(
        query=DefineField('tags', 'array<int>').on('node').if_not_exists(True).default('[]')
    ),
]
