from abc import ABCMeta, abstractmethod

from pydantic import BaseModel

from minager.core import surorm
from minager.core.lexorank import Lexorank
from minager.core.surorm.orm.serializer import Serializer

from . import dto, enums, models, queries, schemas, utils
from .services.move_node import MoveNodeService


class BaseNodeManager(surorm.Manager, metaclass=ABCMeta):
    model: models.Node = models.Node

    @abstractmethod
    async def create(self, data: dict | BaseModel) -> models.Node | None: ...

    @abstractmethod
    async def get(self, id_: str) -> models.Node | None: ...

    @abstractmethod
    async def search(
        self, query: str = '', page: int = 1, size: int = 15, user_id: str | None = None, **kwargs
    ) -> list[schemas.SearchNodeResultSchema]: ...

    @abstractmethod
    async def get_subtree(self, id_: str) -> models.TreeNode | None: ...

    @abstractmethod
    async def add_child(self, id_: str, data: dict) -> models.Node | None: ...

    @abstractmethod
    async def patch(self, id_: str, data: dict) -> models.Node | None: ...

    @abstractmethod
    async def delete(self, id_: str) -> None: ...

    @abstractmethod
    async def move(self, id_: str, to: str, position: enums.MovePosition) -> models.Node: ...


class PalaceNodeManager(BaseNodeManager):
    async def create(self, data: dict) -> models.Node | None:
        self._check_connection()
        query = surorm.Create(self.model).content(data).return_('after')
        response = await self.query(query)
        return models.Node.model_validate(response)

    async def get(self, node_id: str) -> models.Node | None:
        self._check_connection()
        query = surorm.Select(
            surorm.Alias('parent_id', surorm.F.array.first('->child.out')),
            surorm.Alias('ancestors', queries.ancestors_query),
            all_=True,
        ).from_(surorm.F.type.thing('node', node_id))
        node_data: dict | None = await self.select_one(query)
        return models.Node.model_validate(node_data) if node_data else None

    async def search(
        self, query: str = '', page: int = 1, size: int = 15, user_id: str | None = None, **kwargs
    ) -> list[schemas.SearchNodeResultSchema]:
        self._check_connection()
        conditions = []
        if user_id:
            kwargs['owner_id'] = user_id
        if query:
            conditions.append(f'title @@ {surorm.String(query)}')
        if kwargs:
            serializer_class = type('NodeSerializer', (Serializer,), {'model': models.Node})
            serializer = serializer_class()
            serialized_data = [
                f'{field_name} = {serializer.serialize_field(field_name, value)}'
                for field_name, value in kwargs.items()
            ]
            conditions.extend(serialized_data)
        q = (
            surorm.Select(
                'id',
                'title',
                'order',
                surorm.Alias('ancestors', queries.ancestors_query),
            )
            .from_(models.Node)
            .where(*conditions)
            .limit(size)
            .start(size * (page - 1))
        )
        response = await self.select(q)
        return [schemas.SearchNodeResultSchema.model_validate(item) for item in response]

    async def add_child(self, parent_id: str, data: dict) -> models.Node | None:
        self._check_connection()
        # TODO: Must first check if parent node exists
        last_child_order_query = queries.get_last_child_order_query(parent_id)
        last_child_order: str = await self.select_one(last_child_order_query)
        data['order'] = Lexorank.middle(previous=last_child_order)
        child_variable_name = 'child'
        query = surorm.Transaction(
            surorm.DefineVariable(
                child_variable_name,
                surorm.Create(models.Node, only=True).content(data),
            ),
            (
                surorm.Relate('child')
                .from_(surorm.Variable(child_variable_name))
                .to(surorm.Record(models.Node, parent_id))
            ),
        ).return_(surorm.Variable(child_variable_name))
        new_node = await self.query(query)
        return await self.get(new_node.get('id').id) if new_node else None

    async def get_subtree(self, id_: str) -> models.TreeNode:
        self._check_connection()
        stmt = surorm.Select(
            'id',
            'title',
            'order',
            surorm.Alias('parent_id', queries.parent_id_query),
            surorm.Alias('ancestors', queries.ancestors_query),
        ).from_(f'{surorm.F.type.thing('node', id_)}.{{1..2+collect+inclusive}}<-child<-node')
        nodes = await self.query(stmt)
        tree_root = utils.construct_tree(nodes)
        return models.TreeNode.model_validate(tree_root)

    async def get_children(self, uid: str) -> list[models.ListNode]:
        self._check_connection()
        query = surorm.Select('VALUE <-child<-node.{id, title, order}').from_(
            surorm.F.type.thing(models.Node, uid), only=True
        )
        children: list[dict] = await self.select(query)
        validated_children = [
            models.ListNode.model_validate(node_data)
            for node_data in children
            if node_data and isinstance(node_data, dict)
        ]
        # TODO: This sorting is just a temp solution. Fix
        validated_children.sort(key=lambda list_node: list_node.order)
        return validated_children

    async def get_subtree_statistics(self, id_: str) -> dto.NodeSubtreeStatistics:
        self._check_connection()
        query = queries.get_node_statistics_query(id_)
        stats = await self.query(query)
        return dto.NodeSubtreeStatistics.model_validate(stats or {})

    async def get_statistics(self, node_id: str) -> dto.NodeOverallStatistics:
        self._check_connection()
        node = await self.get(node_id)
        subtree_stats = await self.get_subtree_statistics(node_id)
        return dto.NodeOverallStatistics.model_validate(
            {
                'indexes': {},
                'node': node.model_dump(mode='json'),  # TODO: Fix only node statistic data here
                'subtree': subtree_stats,
            }
        )

    async def patch(self, id_: str, data: dict) -> models.Node | None:
        self._check_connection()
        query = surorm.Update(surorm.Record(models.Node, id_)).merge(data)
        await self.query(query.sql())
        return await self.get(id_)

    update = patch

    async def move(
        self,
        id_: str,
        to: str,
        position: enums.MovePosition = enums.MovePosition.last_child,
    ) -> schemas.UpdatedNodeSchema | None:
        service = MoveNodeService(manager=self)
        return await service.move(id_, to, position)

    async def delete(self, uid: str):
        self._check_connection()
        query = surorm.Transaction(
            surorm.DefineVariable('root', surorm.F.type.thing('node', uid)),
            surorm.DefineVariable(
                'descendants',
                (
                    surorm.Select('value id').from_(
                        f'{surorm.Variable('root')}.{{..+collect+inclusive}}<-child<-node.id'
                    )
                ),
            ),
            surorm.Delete('child').where(surorm.In('in', surorm.Variable('descendants'))),
            surorm.Delete(surorm.Variable('descendants')),
        )
        return await self.query(query.sql())

    async def get_subtree_ids(
        self,
        root_id: str,
        limit: int = 30,
        _strategy: str = None,  # Add later
    ) -> list[str]:
        self._check_connection()
        query = surorm.Transaction(
            surorm.DefineVariable('root', surorm.F.type.thing('node', root_id)),
            surorm.DefineVariable(
                'descendants',
                surorm.Select('id', 'title', 'next_optimal_repetition')
                .from_(f'{surorm.Variable('root')}.{{..+collect+inclusive}}<-child<-node')
                .order_by('next_optimal_repetition')
                .limit(limit),
            ),
        ).return_(surorm.Variable('descendants'))
        response = await self.query(query.sql())
        return [node['id'].id for node in response]
