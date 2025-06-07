from api.node.functions import DeleteSubtree, GetSubtreeIds
from api.surorm import SurrealDBManager
from api.surorm.query import Create, Operation, Record, Select, Transaction, Update

from . import enums, schemas, utils
from .requests.add_tag import AddTagRequest, AddTagRequestConfig
from .requests.create_child import CreateChildConfig, CreateChildRequest
from .requests.get_detail import GetNodeDetailConfig, GetNodeDetailRequest
from .requests.get_palace_root import GetPalaceRootConfig, GetPalaceRootRequest
from .requests.get_statistics import (
    GetOverallStatisticsConfig,
    GetOverallStatisticsRequest,
)
from .requests.get_subtree import GetSubtreeConfig, GetSubtreeRequest
from .requests.list import ListNodesRequest, ListNodesRequestConfig
from .requests.move import MoveNodeConfig, MoveNodeRequest
from .requests.remove_tag import RemoveTagRequest, RemoveTagRequestConfig


class PalaceNodeManager(SurrealDBManager):
    async def get_my_palace_root(self, owner_id: str) -> str | None:
        self._check_connection()
        config = GetPalaceRootConfig(owner_id=owner_id)
        response = await GetPalaceRootRequest(db=self, config=config).perform()
        palace_root_id: str = response.raw(many=False)
        return palace_root_id.lstrip('node:') if palace_root_id else None

    async def get(self, node_id: str) -> schemas.NodeDetailSchema | None:
        self._check_connection()
        config = GetNodeDetailConfig(id=node_id)
        response = await GetNodeDetailRequest(db=self, config=config).perform()
        node_schema = schemas.NodeDetailSchema.from_db_response(response.data())
        return node_schema

    async def get_overall_statistics(self, owner_id: str) -> schemas.PalaceStatistics | None:
        self._check_connection()
        config = GetOverallStatisticsConfig(owner_id=owner_id)
        response = await GetOverallStatisticsRequest(db=self, config=config).perform()
        response_data = response.data()
        statistics = (
            response_data[0] if isinstance(response_data, list) and len(response_data) else {}
        )
        return schemas.PalaceStatistics.model_validate(statistics)

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

    async def create(self, **kwargs) -> schemas.NodeDetailSchema | None:
        root_schema = schemas.NodeCreateSchema.model_validate(kwargs)
        query = Create('node').content(root_schema.model_dump_surreal()).return_('after')
        response = await self.query(query)
        return schemas.NodeDetailSchema.model_validate(response.data()[0])

    async def create_child(
        self, parent_uid: str, data: dict | schemas.NodeCreateSchema
    ) -> schemas.NodeDetailSchema | None:
        self._check_connection()
        config = CreateChildConfig(parent_id=parent_uid, data=data)
        request = CreateChildRequest(db=self, config=config)
        response = await request.perform()
        new_node = response.data()
        if not new_node:
            return
        return await self.get(utils.parse_id(new_node.get('id'))[1])

    async def get_subtree(self, uid: str) -> schemas.TreeNodeItemSchema:
        self._check_connection()
        config = GetSubtreeConfig(root_id=uid)
        request = GetSubtreeRequest(db=self, config=config)
        response = await request.perform()
        root = response.raw(many=False)
        root['ancestors'] = root['ancestors'][::-1] if root['ancestors'] is not None else None
        return schemas.model_validate_tree(root)

    async def patch(
        self, uid: str, data: dict | schemas.NodeEditSchema
    ) -> schemas.NodeDetailSchema:
        self._check_connection()
        if isinstance(data, dict):
            data = schemas.NodeEditSchema.model_validate(data)
        print(data.model_dump(mode='json', exclude_unset=True))
        print(data.model_dump_surreal(exclude_unset=True))
        query = Update(Record('node', uid)).merge(data.model_dump_surreal(exclude_unset=True))
        await self.query(query.sql())
        return await self.get(uid)

    async def add_tag(self, node_id: str, tag_ids: list[str]) -> schemas.UpdatedNodeSchema:
        self._check_connection()
        config = AddTagRequestConfig(node_id=node_id, tag_ids=tag_ids)
        response = await AddTagRequest(db=self, config=config).perform()
        return schemas.UpdatedNodeSchema.model_validate(response.data())

    async def remove_tag(self, node_id: str, tag_ids: list[str]) -> schemas.UpdatedNodeSchema:
        self._check_connection()
        config = RemoveTagRequestConfig(node_id=node_id, tag_ids=tag_ids)
        response = await RemoveTagRequest(db=self, config=config).perform()
        return schemas.UpdatedNodeSchema.model_validate(response.data())

    async def move(
        self, node_id: str, target_id: str, move_position: int
    ) -> schemas.UpdatedNodeSchema | None:
        config = MoveNodeConfig(node_id=node_id, target_id=target_id, move_position=move_position)
        request = MoveNodeRequest(db=self, config=config)
        response = await request.perform()
        return response.instances(schemas.UpdatedNodeSchema, many=False) if response else None

    async def delete(self, uid: str):
        self._check_connection()
        query = Transaction().perform(DeleteSubtree(f'node:{uid}'))
        await self.query(query.sql())

    async def get_subtree_ids(
        self,
        root_id: str,
        limit: int = 30,
        ordering: enums.NodeOrdering = enums.NodeOrdering.outdated,
    ) -> list[str]:
        self._check_connection()
        query = (
            Select()
            .from_('node')
            .columns('id', 'next_optimal_repetition')
            .where('is_learn = true', Operation('in', 'id', GetSubtreeIds(Record('node', root_id))))
            .order_by('next_optimal_repetition', direction='asc')
            .limit(limit)
        )
        response = await self.query(query.sql())
        return [node.get('id').split(':')[-1] for node in response.raw()]
