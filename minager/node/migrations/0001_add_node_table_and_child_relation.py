from surorm.data_model import Float, Int, String
from surorm.functions import F
from surorm.migrations import MigrationOperation
from surorm.operators import Add
from surorm.statements import DefineField, DefineTable

operations = [
    MigrationOperation(
        query=DefineTable('node').type('normal').schemafull(True).if_not_exists(True),
    ),
    MigrationOperation(
        query=(DefineTable('child').type('relation', 'node', 'node').schemafull(True).if_not_exists(True))
    ),
    MigrationOperation(query=DefineField('is_learn', 'bool').on('node').if_not_exists(True).default('true')),
    MigrationOperation(query=DefineField('owner_id', 'string').on('node').if_not_exists(True)),
    MigrationOperation(query=DefineField('title', 'string').on('node').if_not_exists(True)),
    MigrationOperation(
        query=DefineField('questions', 'string').on('node').if_not_exists(True).default(String(''))
    ),
    MigrationOperation(query=DefineField('order', 'string').on('node').if_not_exists(True)),
    MigrationOperation(
        query=DefineField('content', 'string').on('node').if_not_exists(True).default(String(''))
    ),
    MigrationOperation(query=DefineField('size', 'number').on('node').if_not_exists(True).default(Int(0))),
    MigrationOperation(query=DefineField('cpr', 'number').on('node').if_not_exists(True).default(Int(0))),
    MigrationOperation(
        query=DefineField('last_rating', 'number').on('node').if_not_exists(True).default(Float(0))
    ),
    MigrationOperation(
        query=DefineField('difficulty', 'number').on('node').if_not_exists(True).default(Float(2.4))
    ),
    MigrationOperation(
        query=DefineField('owner_views', 'number').on('node').if_not_exists(True).default(Int(0))
    ),
    MigrationOperation(
        query=DefineField('repetitions', 'number').on('node').if_not_exists(True).default(Int(0))
    ),
    MigrationOperation(
        query=DefineField('last_interval', 'number').on('node').if_not_exists(True).default(Int(0))
    ),
    MigrationOperation(
        query=DefineField('last_repetition', 'datetime').on('node').if_not_exists(True).default(F.time.now())
    ),
    MigrationOperation(
        query=(
            DefineField('next_optimal_repetition', 'datetime')
            .on('node')
            .if_not_exists(True)
            .default(Add(F.time.now(), F.duration.from_days(1)))
        )
    ),
]
