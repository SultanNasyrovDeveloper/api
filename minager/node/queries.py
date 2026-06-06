from minager.core import surorm

parent_id_query = surorm.F.array.first('->child.out')
ancestors_query = surorm.Select('id', 'title').from_('$this.{..+collect}->child->node')


def get_last_child_order_query(parent_id: str) -> surorm.Expression:
    parent = surorm.Record('node', parent_id)
    return (
        surorm.Select('value order')
        .from_('node')
        .where(f'->(child where out == {parent})')
        .order_by('order', direction='desc')
        .limit(1)
    )


def get_node_statistics_query(node_id: str) -> surorm.Expression:
    return surorm.Transaction(
        surorm.DefineVariable('node', surorm.F.type.thing('node', node_id)),
    ).return_(
        surorm.Select(
            surorm.Alias('average_rating', surorm.F.math.mean('last_rating')),
            surorm.Alias('count', surorm.F.count()),
            surorm.Alias('size', surorm.F.math.sum('size')),
            surorm.Alias('owner_views', surorm.F.math.sum('owner_views')),
            surorm.Alias('repetitions', surorm.F.math.sum('repetitions')),
            surorm.Alias(
                'outdated',
                surorm.F.math.sum('IF next_optimal_repetition <= time::now() THEN 1 ELSE 0 END'),
            ),
            surorm.Alias('not_visited', surorm.F.math.sum('IF owner_views = 0 THEN 1 ELSE 0 END')),
            surorm.Alias('empty', surorm.F.math.sum('IF size = 0 THEN 1 ELSE 0 END')),
        )
        .from_(f'{surorm.Variable("node")}.{{..+collect}}<-child<-node')
        .group(all_=True)
    )
