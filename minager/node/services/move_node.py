from ..enums import MovePosition


class MoveNodeService:
    async def move(self, node_id: str, to_id: str, position: MovePosition):
        pass

    async def get_new_position(self):
        pass
