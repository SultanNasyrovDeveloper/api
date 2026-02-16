from minager.core import surorm

operations = [
    surorm.MigrationOperation(
        query=surorm.DefineAnalyzer('autocomplete').filters('lowercase', 'ngram(1, 10)')
    ),
    surorm.MigrationOperation(
        query=(
            surorm.DefineIndex('node_title_idx')
            .on('node')
            .columns('title')
            .search('autocomplete', 'bm25', is_highlighted=True)
        )
    ),
]
