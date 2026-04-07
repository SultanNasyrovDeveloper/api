from abc import ABCMeta, abstractmethod

from pydantic import BaseModel

from minager.core import surorm
from minager.core.lexorank import Lexorank

from . import dto, models, queries, schemas, utils
from .requests.list import ListNodesRequest, ListNodesRequestConfig
from .requests.move import MoveNodeConfig, MoveNodeRequest
from .services.node_index.node_indexes import NodeOverallIndex


class BaseNodeManager(surorm.Manager, metaclass=ABCMeta):
    model: models.Node = models.Node

    @abstractmethod
    async def create(self, data: dict | BaseModel) -> models.Node: ...

    @abstractmethod
    async def get(self, id_: str) -> models.Node: ...

    @abstractmethod
    async def add_child(self, id_: str, data: dict): ...

    # @abstractmethod
    # async def move_node(self):
    #     pass

    #
    # @abstractmethod
    # async def search(self): pass
    #
    # @abstractmethod
    # async def get_subtree(self): pass
    #
    # @abstractmethod
    # async def get_children(self): pass
    #
    # @abstractmethod
    # async def patch(self): pass
    #
    # @abstractmethod
    # async def delete(self): pass


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

    async def get_my_palace_root(self, owner_id: str) -> str | None:
        self._check_connection()
        query = (
            surorm.Select('value id')
            .from_('node')
            .where(surorm.F.array.is_empty('->child->node'), surorm.Equals('owner_id', owner_id))
        )
        response = await self.query(query.sql())
        palace_root_id: str = response.raw(many=False)
        return palace_root_id.lstrip('node:') if palace_root_id else None

    async def add_child(self, parent_id: str, data: dict) -> models.Node | None:
        self._check_connection()
        last_child_order_query = queries.get_last_child_order_query(parent_id)
        last_child_order: str = await self.select_one(last_child_order_query)
        data['order'] = Lexorank.middle(previous=last_child_order)
        child_variable_name = 'child'
        query = surorm.Transaction(
            surorm.DefineVariable(
                child_variable_name, surorm.Create(models.Node, only=True).content(data)
            ),
            (
                surorm.Relate('child')
                .from_(surorm.Variable(child_variable_name))
                .to(surorm.Record(models.Node, parent_id))
            ),
        ).return_(surorm.Variable(child_variable_name))
        new_node = await self.query(query)
        return await self.get(new_node.get('id').id) if new_node else None

    async def list_(
        self,
        owner_id: str,
        search: str,
        page: int = 1,
        per_page: int = 10,
    ) -> list[schemas.NodeListItemSchema] | None:
        self._check_connection()
        config = ListNodesRequestConfig(
            owner_id=owner_id, search=search, page=page, per_page=per_page
        )
        response = await ListNodesRequest(db=self, config=config).perform()
        nodes = response.data()
        return (
            [schemas.NodeListItemSchema.model_validate(node) for node in nodes]
            if isinstance(nodes, list)
            else None
        )

    async def get_subtree(self, uid: str) -> schemas.TreeNodeItemSchema:
        self._check_connection()
        stmt = surorm.Select(
            'id',
            'title',
            'order',
            surorm.Alias('parent_id', queries.parent_id_query),
            surorm.Alias('ancestors', queries.ancestors_query),
        ).from_(f'{surorm.F.type.thing('node', uid)}.{{1..2+collect+inclusive}}<-child<-node')
        nodes = await self.query(stmt)
        tree_root = utils.construct_tree(nodes)
        return schemas.TreeNodeItemSchema.model_validate(tree_root)

    async def get_children(self, uid: str) -> list[schemas.NodeListItemSchema]:
        self._check_connection()
        query = surorm.Select('VALUE <-child<-node.{id, title, order}').from_(
            surorm.F.type.thing(models.Node, uid), only=True
        )
        children: list[dict] = await self.select(query)
        return [
            schemas.NodeListItemSchema.model_validate(node_data)
            for node_data in children
            if node_data and isinstance(node_data, dict)
        ]

    async def get_subtree_statistics(self, root_id: str) -> dto.NodeSubtreeStatistics:
        self._check_connection()
        stats = await self.query(queries.get_node_statistics_query(root_id))
        return dto.NodeSubtreeStatistics.model_validate(stats)

    async def get_statistics(self, node_id: str) -> dto.NodeOverallStatistics:
        self._check_connection()
        node = await self.get(node_id)
        subtree_stats = await self.get_subtree_statistics(node_id)
        index = NodeOverallIndex(node, subtree_stats)
        data = index.calculate()
        return dto.NodeOverallStatistics.model_validate(
            {
                'indexes': data,
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
        self, node_id: str, target_id: str, move_position: int
    ) -> schemas.UpdatedNodeSchema | None:
        """
        TODO: add validation for:
          - Node exists
          - Target exists
          - Not moving node to itself
          - Not creating cycles in the tree
          - Not moving node to be its own descendant
        """
        config = MoveNodeConfig(node_id=node_id, target_id=target_id, move_position=move_position)
        request = MoveNodeRequest(db=self, config=config)
        response = await request.perform()
        return response.instances(schemas.UpdatedNodeSchema, many=False) if response else None

    async def delete(self, uid: str):
        self._check_connection()
        query = surorm.Transaction(
            surorm.DefineVariable('root', surorm.F.type.thing('node', uid)),
            surorm.DefineVariable(
                'nodes', f'{surorm.Variable('root')}.{{..+collect+inclusive}}<-child<-node.id'
            ),
            surorm.Delete('child').where(
                surorm.Or(
                    surorm.In('in', surorm.Variable('nodes')),
                    surorm.In('out', surorm.Variable('nodes')),
                )
            ),
            surorm.Delete('node').where(surorm.In('in', surorm.Variable('nodes'))),
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
