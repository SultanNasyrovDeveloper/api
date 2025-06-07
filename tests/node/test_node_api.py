from fastapi import status

from api.node import schemas


BASE_URL = 'api/v1/mind-palace/nodes/'


async def test_create_node(fake, palace_client):
    node_data = {'owner_id': 'test_user_id', 'title': fake.pystr(), 'questions': fake.pystr()}
    async with palace_client as session:
        new_node = await session.create(**node_data)
    assert new_node and isinstance(new_node, schemas.NodeDetailSchema)


async def test_get_node(api_client, api_user, fake, palace_client):
    node_data = {'owner_id': api_user['id'], 'title': fake.pystr(), 'questions': fake.pystr()}
    async with palace_client as session:
        node = await session.create(**node_data)
    url = BASE_URL + node.id
    response = api_client.get(url)
    node.ancestors = [{'id': node.id, 'title': node.title}]
    assert response.json() == node.model_dump(mode='json')


async def test_get_my_palace_root(api_client, api_user, fake, palace_client):
    url = BASE_URL + 'my-palace-root'
    root_node_data = {
        'owner_id': api_user['id'],
        'title': fake.pystr(),
        'question': fake.pystr()
    }
    async with palace_client as session:
        root = await session.create(**root_node_data)
    response = api_client.get(url)
    assert response.json() == root.id


async def test_create_child(api_client, api_user, fake, palace_client):
    async with palace_client as session:
        node_data = {'owner_id': api_user['id'], 'title': fake.pystr(), 'questions': fake.pystr()}
        parent = await session.create(**node_data)
    url = BASE_URL + f'{parent.id}/add-child'
    child_data = {
        'owner_id': api_user['id'],
        'title': fake.pystr(),
        'questions': fake.pystr(),
        'is_learn': False,
        'order': 'bbbbbb'
    }
    response = api_client.post(url, json=child_data)
    response_data = response.json()
    assert response.status_code == status.HTTP_201_CREATED
    assert response_data
    async with palace_client as session:
        expected = await session.get(response.json()['id'])
    assert response_data == expected.model_dump(mode='json')


async def test_get_subtree_ids(subtree_ids, api_client):
    url = BASE_URL + f'{subtree_ids[0]}/subtree-ids?limit={len(subtree_ids)}'
    response = api_client.get(url)
    response_data = response.json()
    assert response_data == subtree_ids


