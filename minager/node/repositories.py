from surorm.base import DataType
from surorm.data_model import RecordID, String
from surorm.functions import F
from surorm.operators import Equals, In, Matches
from surorm.repository import Repository
from surorm.statements import (
    Alias,
    Create,
    DefineVariable,
    Delete,
    Relate,
    Select,
    TransactionReturn,
    Update,
    Variable,
)

from . import dto, enums, models, queries, schemas


class NodeRepository(Repository[models.Node]):
    async def create(self, data: dict) -> models.Node | None:
        query = Create(models.Node).content(data).return_('after')
        result = await self._session.execute(query)
        return result.first(as_=models.Node)

    async def search(
        self, query: str = '', page: int = 1, size: int = 15, **kwargs
    ) -> list[schemas.SearchNodeResultSchema]:
        conditions: list = []
        model_class = self.model_class
        assert model_class
        if query:
            conditions.append(Matches(models.Node.title, String(query)))
        for field_name, value in kwargs.items():
            column = getattr(model_class, field_name)
            if not isinstance(value, DataType):
                column_data_type = model_class.get_data_type(field_name)
                value = column_data_type(value)
            conditions.append(Equals(column, value))
        stmt = (
            Select(models.Node.id, models.Node.title, models.Node.order, models.Node.ancestors)
            .from_(models.Node)
            .where(*conditions)
            .limit(size)
            .start(size * (page - 1))
        )
        result = await self.execute(stmt)
        return result.all(as_=models.ListNode)

    async def get_last_child_order(self, parent_id: str) -> str:
        parent = F.type.thing('node', parent_id)
        query = (
            Select('value order')
            .from_(models.Node)
            .where(f'->(child where out == {parent})')
            .order_by(models.Node.order, direction='DESC')
            .limit(1)
        )
        result = await self.execute(query)
        values = result.dicts()
        return values[0] if values else None

    async def get_subtree_nodes(self, id_: str) -> list[dict]:
        stmt = Select(
            models.Node.id, models.Node.title, models.Node.order, models.Node.parent_id, models.Node.ancestors
        ).from_(f'{F.type.thing(models.Node, id_)}.{{1..2+collect+inclusive}}<-child<-node')
        result = await self.execute(stmt)
        return result.all()

    async def get_children(self, uid: str) -> list[models.ListNode]:
        # TODO: This query could be more readable by using where clause and filter by relation fields rather than like this
        query = Select('VALUE <-child<-node.{id, title, order}').from_(
            F.type.thing(models.Node, uid), only=True
        )
        result = await self.execute(query)
        validated_children = result.all(as_=models.ListNode)
        validated_children.sort(key=lambda list_node: list_node.order)
        return validated_children

    async def get_subtree_statistics(self, id_: str) -> dto.NodeSubtreeStatistics:
        model_class = self._model()
        query = (
            Select(
                Alias('average_rating', F.math.mean('last_rating')),
                Alias('count', F.count()),
                Alias('size', F.math.sum('size')),
                Alias('owner_views', F.math.sum('owner_views')),
                Alias('repetitions', F.math.sum('repetitions')),
                Alias(
                    'outdated',
                    F.math.sum('IF next_optimal_repetition <= time::now() THEN 1 ELSE 0 END'),
                ),
                Alias('not_visited', F.math.sum('IF owner_views = 0 THEN 1 ELSE 0 END')),
                Alias('empty', F.math.sum('IF size = 0 THEN 1 ELSE 0 END')),
            )
            .from_(f'{F.type.thing(model_class, id_)}.{{..+collect}}<-child<-node')
            .group_by(all_=True)
        )
        result = await self.execute(query)
        results_list = result.dicts()
        return dto.NodeSubtreeStatistics.model_validate(results_list[0] if len(results_list) else {})

    async def delete(self, uid: str):
        model_class = self._model()
        query = (
            DefineVariable('root', F.type.thing(model_class, uid)),
            DefineVariable(
                'descendants',
                Select('value id').from_(f'{Variable("root")}.{{..+collect+inclusive}}<-child<-node.id'),
            ),
            Delete('child').where(In('in', Variable('descendants'))),
            Delete(Variable('descendants')),
        )
        return await self.execute_many(*query)

    async def get_subtree_ids(
        self,
        root_ids: list[str],
        filter_: enums.SubtreeFilter = enums.SubtreeFilter.all,
        order: enums.TraversalOrder = enums.TraversalOrder.bfs,
        limit: int = 30,
    ) -> list[str]:
        query_builder = queries.SubtreeIdsQuery()
        query = query_builder.build(root_ids, filter_, order)
        query = query.limit(limit)
        result = await self.execute(query)
        return [record['id'].id for record in result.all()]

    async def get_first_child_order(self, parent_id: str) -> str:
        parent = F.type.thing('node', parent_id)
        query = (
            Select('value order')
            .from_(models.Node)
            .where(f'->(child where out == {parent})')
            .order_by(models.Node.order, direction='ASC')
            .limit(1)
        )
        result = await self.execute(query)
        values = result.dicts()
        return values[0] if values else None

    async def get_move_validation_context(self, node_id: str, target_id: str) -> dict:
        query = (
            DefineVariable('source', Select(models.Node.id).from_(RecordID(models.Node, node_id), only=True)),
            DefineVariable(
                'target', Select(models.Node.id).from_(RecordID(models.Node, target_id), only=True)
            ),
            DefineVariable(
                'cycle',
                Select('value id')
                .from_(f'{F.type.thing(models.Node, node_id)}.{{..}}<-child<-node')
                .where(f'id == {F.type.thing(models.Node, target_id)}')
                .limit(1),
            ),
            TransactionReturn('{source: $source, target: $target, has_cycle: $cycle}'),
        )
        results = await self.execute_many(*query)
        return results[-1].first() or {}

    async def get_sibling_order_context(self, target_id: str, before: bool) -> dict | None:
        comparison = '<' if before else '>'
        direction = 'DESC' if before else 'ASC'
        query = (
            DefineVariable(
                'target',
                Select(models.Node.order, Alias('parent_id', F.array.first('->child.out'))).from_(
                    F.type.thing(models.Node, target_id), only=True
                ),
            ),
            DefineVariable(
                'neighbour',
                F.array.first(
                    Select('value order')
                    .from_(models.Node)
                    .where('->(child where out == $target.parent_id)', f'order {comparison} $target.order')
                    .order_by(models.Node.order, direction=direction)
                    .limit(1)
                ),
            ),
            TransactionReturn('{new_parent: $target.parent_id, order: $target.order, neighbour: $neighbour}'),
        )
        results = await self.execute_many(*query)
        data = results[-1].first()
        if not data:
            return None
        previous, next_ = (data['neighbour'], data['order']) if before else (data['order'], data['neighbour'])
        new_parent_id = RecordID.to_python(data['new_parent']).id_
        return {'new_parent': new_parent_id, 'previous': previous, 'next': next_}

    async def move(self, node_id: str, new_parent_id: str, order: str) -> None:
        query = (
            Delete('child').where(f'in == {F.type.thing(models.Node, node_id)}'),
            Relate('child').from_(RecordID(models.Node, node_id)).to(RecordID(models.Node, new_parent_id)),
            Update(models.Node).set(order=order).where(f'id == {F.type.thing(models.Node, node_id)}'),
        )
        await self.execute_many(*query)
