from ..core import surorm
from . import dto, queries, schemas, utils
from .requests.create_child import CreateChildConfig, CreateChildRequest
from .requests.get_palace_root import GetPalaceRootConfig, GetPalaceRootRequest
from .requests.list import ListNodesRequest, ListNodesRequestConfig
from .requests.move import MoveNodeConfig, MoveNodeRequest


class PalaceNodeManager(surorm.Manager):
    async def get_my_palace_root(self, owner_id: str) -> str | None:
        self._check_connection()
        config = GetPalaceRootConfig(owner_id=owner_id)
        response = await GetPalaceRootRequest(db=self, config=config).perform()
        palace_root_id: str = response.raw(many=False)
        return palace_root_id.lstrip('node:') if palace_root_id else None

    async def create(self, **kwargs) -> schemas.NodeDetailSchema | None:
        root_schema = schemas.NodeCreateSchema.model_validate(kwargs)
        query = surorm.Create('node').content(root_schema.model_dump_surreal()).return_('after')
        response = await self.query(query)
        return schemas.NodeDetailSchema.model_validate(response[0])

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

    async def get(self, node_id: str) -> schemas.NodeDetailSchema | None:
        self._check_connection()
        query = surorm.Select(
            surorm.Alias('parent_id', surorm.F.array.first('->child.out')),
            surorm.Alias('ancestors', queries.ancestors_query),
            all_=True,
        ).from_(surorm.F.type.thing('node', node_id))
        node_data: dict | None = await self.query(query)
        return schemas.NodeDetailSchema.model_validate(node_data) if node_data else None

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
        return [schemas.NodeListItemSchema.model_validate(node_data) for node_data in children]

    async def get_subtree_statistics(self, root_id: str) -> dto.SubtreeStatistics:
        self._check_connection()
        query = surorm.Transaction(
            surorm.DefineVariable('node', surorm.F.type.thing('node', root_id)),
            surorm.Select(
                surorm.Alias('total_nodes', surorm.F.count()),
                surorm.Alias('average_rating', surorm.F.math.mean('last_rating')),
                surorm.Alias('total_size', surorm.F.math.sum('size')),
                surorm.Alias('total_owner_views', surorm.F.math.sum('owner_views')),
                surorm.Alias('total_repetitions', surorm.F.math.sum('repetitions')),
                surorm.Alias(
                    'total_outdated',
                    surorm.F.math.sum(
                        'IF next_optimal_repetition <= time::now() THEN 1 ELSE 0 END'
                    ),
                ),
                surorm.Alias(
                    'total_not_visited', surorm.F.math.sum('IF owner_views = 0 THEN 1 ELSE 0 END')
                ),
                surorm.Alias('total_empty', surorm.F.math.sum('IF size = 0 THEN 1 ELSE 0 END')),
            ).from_(f'{surorm.Variable('node')}.{{..+collect+inclusive}}<-child<-node'),
        )
        stats = await self.query(query)
        return dto.SubtreeStatistics.model_validate(stats)

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
        config = MoveNodeConfig(node_id=node_id, target_id=target_id, move_position=move_position)
        request = MoveNodeRequest(db=self, config=config)
        response = await request.perform()
        return response.instances(schemas.UpdatedNodeSchema, many=False) if response else None

    async def delete(self, uid: str):
        self._check_connection()
        query = surorm.Transaction(
            surorm.DefineVariable('root', surorm.F.type.thing('node', uid)),
            surorm.DefineVariable(
                'nodes', f'{surorm.Variable('root')}.{{..+collect+inclusive}}->child->node.id'
            ),
            surorm.Delete('child').where(
                surorm.Or(
                    surorm.In('in', surorm.Variable('nodes')),
                    surorm.In('out', surorm.Variable('nodes')),
                )
            ),
            surorm.Delete('node').where(surorm.In('in', surorm.Variable('nodes'))),
        )
        # response = await self.query(query.sql())
        # print(response)

    async def get_subtree_ids(
        self,
        root_id: str,
        limit: int = 30,
        _strategy: str = None,  # Add later
    ) -> list[str]:
        self._check_connection()
        query = (
            surorm.Select('id', 'title', 'next_optimal_repetition')
            .from_(
                f'{surorm.F.type.thing('node_id', root_id)}.{{..+collect+inclusive}}<-child<-node'
            )
            .order_by('next_optimal_repetition')
            .limit(limit)
        )
        response = await self.query(query.sql())
        return [node['id'].id for node in response]
