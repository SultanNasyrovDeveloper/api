from minager.core import surorm
from minager.core.surorm.migrations import MigrationOperation

operations = [
    MigrationOperation(
        query=surorm.DefineTable('node').type('normal').schemafull(True).if_not_exists(True),
    ),
    MigrationOperation(
        query=(
            surorm.DefineTable('child').type('relation', 'node', 'node').schemafull(True).if_not_exists(True)
        )
    ),
    MigrationOperation(
        query=surorm.DefineField('is_learn', 'bool').on('node').if_not_exists(True).default('true')
    ),
    MigrationOperation(query=surorm.DefineField('owner_id', 'string').on('node').if_not_exists(True)),
    MigrationOperation(query=surorm.DefineField('title', 'string').on('node').if_not_exists(True)),
    MigrationOperation(
        query=surorm.DefineField('questions', 'string')
        .on('node')
        .if_not_exists(True)
        .default(surorm.String(''))
    ),
    MigrationOperation(query=surorm.DefineField('order', 'string').on('node').if_not_exists(True)),
    MigrationOperation(
        query=surorm.DefineField('content', 'string')
        .on('node')
        .if_not_exists(True)
        .default(surorm.String(''))
    ),
    MigrationOperation(
        query=surorm.DefineField('size', 'number').on('node').if_not_exists(True).default(surorm.Number(0))
    ),
    MigrationOperation(
        query=surorm.DefineField('cpr', 'number').on('node').if_not_exists(True).default(surorm.Number(0))
    ),
    MigrationOperation(
        query=surorm.DefineField('last_rating', 'number')
        .on('node')
        .if_not_exists(True)
        .default(surorm.Number(0))
    ),
    MigrationOperation(
        query=surorm.DefineField('difficulty', 'number')
        .on('node')
        .if_not_exists(True)
        .default(surorm.Number(2.4))
    ),
    MigrationOperation(
        query=surorm.DefineField('owner_views', 'number')
        .on('node')
        .if_not_exists(True)
        .default(surorm.Number(0))
    ),
    MigrationOperation(
        query=surorm.DefineField('repetitions', 'number')
        .on('node')
        .if_not_exists(True)
        .default(surorm.Number(0))
    ),
    MigrationOperation(
        query=surorm.DefineField('last_interval', 'number')
        .on('node')
        .if_not_exists(True)
        .default(surorm.Number(0))
    ),
    MigrationOperation(
        query=surorm.DefineField('last_repetition', 'datetime')
        .on('node')
        .if_not_exists(True)
        .default(surorm.F.time.now())
    ),
    MigrationOperation(
        query=(
            surorm.DefineField('next_optimal_repetition', 'datetime')
            .on('node')
            .if_not_exists(True)
            .default(surorm.Add(surorm.F.time.now(), surorm.F.duration.from_days(1)))
        )
    ),
]
