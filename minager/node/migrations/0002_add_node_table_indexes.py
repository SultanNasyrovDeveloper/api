from minager.surorm.migrations import MigrationOperation
from minager.surorm.query import DefineAnalyzer, DefineIndex

operations = [
    MigrationOperation(query=DefineAnalyzer('autocomplete').filters('lowercase', 'ngram(1, 10)')),
    MigrationOperation(
        query=(
            DefineIndex('node_title_idx')
            .on('node')
            .columns('title')
            .search('autocomplete', 'bm25', is_highlighted=True)
        )
    ),
]
