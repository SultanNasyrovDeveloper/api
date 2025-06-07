from api.surorm.migrations import MigrationOperation
from api.surorm.query import DefineFunction
from api.node import functions


operations = [
    MigrationOperation(
        query=(
            DefineFunction(functions.GetAncestors.name)
            .args('$node: record')
            .body(functions.GetAncestors.body)
            .if_not_exists(True)
        )
    ),
    MigrationOperation(
        query=(
            DefineFunction(functions.DeleteSubtree.name)
            .args('$root: record')
            .body(functions.DeleteSubtree.body)
            .if_not_exists(True)
        )
    )
]