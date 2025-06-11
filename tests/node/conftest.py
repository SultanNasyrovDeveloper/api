from random import randrange

import pytest

from minager.node.managers import PalaceNodeManager


@pytest.fixture
def palace_client(app_config):
    return PalaceNodeManager(config=app_config.palace_node_db)


@pytest.fixture
async def subtree(api_user, fake, palace_client):
    async with palace_client as session:
        root = await session.create(
            **{'owner_id': api_user['id'], 'title': fake.pystr(), 'questions': fake.pystr()}
        )
        root_children = []
        for _ in range(10):
            child = await session.create_child(
                root.id,
                {'owner_id': api_user['id'], 'title': fake.pystr(), 'questions': fake.pystr()},
            )
            root_children.append(child)
        root.children = root_children
        for child in root_children:
            child.children = []
            for _ in range(randrange(3, 8)):
                grand_child = await session.create_child(
                    child.id,
                    {'owner_id': api_user['id'], 'title': fake.pystr(), 'questions': fake.pystr()},
                )
                child.children.append(grand_child)
    return root


@pytest.fixture
def subtree_ids(subtree):
    ids = [subtree.id]
    for child in subtree.children:
        ids.append(child.id)
    for child in subtree.children:
        for grandchild in child.children:
            ids.append(grandchild.id)
    return ids
