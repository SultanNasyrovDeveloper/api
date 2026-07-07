from minager.core.lexorank import Lexorank

from . import dto, exceptions, models, utils
from .repositories import NodeRepository


class NodeService:
    def __init__(self, repository: NodeRepository):
        self.repository = repository

    async def get(self, id_: str, viewer_id: str) -> models.Node:
        node = await self.repository.get(id_)
        if not node:
            raise exceptions.NodeNotFoundError
        # TODO: update only once per some period of time(~30 min). Can be abused
        if node.owner_id == viewer_id:
            node.owner_views += 1
            await self.repository.save(node)
        return node

    async def get_subtree(self, id_: str):
        # TODO: Handle node not found
        nodes = await self.repository.get_subtree_nodes(id_)
        tree_root = utils.construct_tree(nodes)
        return models.TreeNode.model_validate(tree_root)

    async def add_child(self, parent_id: str, data: dict) -> models.Node | None:
        parent = await self.repository.get(parent_id)
        if not parent:
            raise exceptions.NodeNotFoundError
        last_child_order = await self.repository.get_last_child_order(parent_id)
        data['order'] = Lexorank.middle(previous=last_child_order)
        # TODO: Use a transaction here
        new_node = await self.repository.create(data)
        await self.repository.relate(new_node, models.Child, parent)
        return await self.repository.get(new_node.id.id_)

    async def get_statistics(self, node_id: str) -> dto.NodeOverallStatistics:
        node = await self.repository.get(node_id)
        if not node:
            raise exceptions.NodeNotFoundError
        subtree_stats = await self.repository.get_subtree_statistics(node_id)
        return dto.NodeOverallStatistics.model_validate(
            {'node': node.model_dump(mode='json'), 'subtree': subtree_stats}
        )

    async def update(self, id_: str, data: dict) -> models.Node:
        node = await self.repository.get(id_)
        if not node:
            raise exceptions.NodeNotFoundError
        updated = await self.repository.update(node, **data)
        if not updated:
            raise exceptions.NodeNotFoundError
        return updated
