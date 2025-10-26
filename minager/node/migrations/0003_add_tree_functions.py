from minager.node import functions
from minager.surorm import DefineFunction
from minager.surorm.migrations import MigrationOperation

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
    ),
]
