from minager import surorm
from minager.surorm import Record, Select

parent_id_query = surorm.F.array.first('->child.out')
ancestors_query = surorm.Select('id', 'title').from_('$this.{..+collect}->child->node')


def get_last_child_order_query(parent_id: str) -> Select:
    parent = Record('node', parent_id)
    return (
        Select('value order')
        .from_('node')
        .where(f'->(child where out == {parent})')
        .order_by('order', direction='desc')
        .limit(1)
    )
