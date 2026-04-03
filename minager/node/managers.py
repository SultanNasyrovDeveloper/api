from abc import ABCMeta, abstractmethod

from pydantic import BaseModel

from ..core import surorm
from . import dto, models, queries, schemas, utils
from .requests.create_child import CreateChildConfig, CreateChildRequest
from .requests.list import ListNodesRequest, ListNodesRequestConfig
from .requests.move import MoveNodeConfig, MoveNodeRequest
from .services.node_index.node_indexes import NodeOverallIndex


class BaseNodeManager(surorm.Manager, metaclass=ABCMeta):
    model: models.Node = models.Node

    # @abstractmethod
    # async def create(self, data: dict | BaseModel) -> models.Node: pass

    @abstractmethod
    async def get(self, id_: str) -> models.Node:
        pass

    #
    # @abstractmethod
    # async def add_child(self): pass
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

    async def create(self, data: dict | BaseModel) -> schemas.NodeDetailSchema | None:
        """
        Create node with input data validation.
        """
        self._check_connection()
        root_schema = (
            schemas.NodeCreateSchema.model_validate(data)
            if not isinstance(data, schemas.NodeCreateSchema)
            else data
        )
        query = surorm.Create('node').content(root_schema.model_dump_surreal()).return_('after')
        response = await self.query(query)
        return schemas.NodeDetailSchema.model_validate(response)

    async def create_child(
        self, parent_uid: str, data: dict | schemas.NodeCreateSchema
    ) -> schemas.NodeDetailSchema | None:
        self._check_connection()
        config = CreateChildConfig(parent_id=parent_uid, data=data)
        request = CreateChildRequest(db=self, config=config)
        new_node = await request.perform()
        if not new_node:
            return None
        return await self.get(new_node.get('id').id)

    async def get(self, node_id: str) -> models.Node | None:
        self._check_connection()
        query = surorm.Select(
            surorm.Alias('parent_id', surorm.F.array.first('->child.out')),
            surorm.Alias('ancestors', queries.ancestors_query),
            all_=True,
        ).from_(surorm.F.type.thing('node', node_id))
        node_data: dict | None = await self.select_one(query)
        return models.Node.model_validate(node_data) if node_data else None

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
            surorm.F.type.thing('node', uid), only=True
        )
        children: list[dict] = await self.query(query)
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

    async def patch(
        self, uid: str, data: dict | schemas.NodeEditSchema
    ) -> schemas.NodeDetailSchema:
        self._check_connection()
        data = schemas.NodeEditSchema.model_validate(data)
        query = surorm.Update(surorm.Record('node', uid)).merge(
            data.model_dump_surreal(exclude_unset=True)
        )
        await self.query(query.sql())
        return await self.get(uid)

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
