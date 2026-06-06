import pytest
from faker import Faker
from fastapi import status
from httpx import AsyncClient

from minager.node.enums import MovePosition
from minager.node.managers import PalaceNodeManager
from minager.node.models import Node

from ..conftest import UserTestContext

BASE_URL = '/api/v1/node/nodes/'


# =============================================================================
# GET /api/v1/node/nodes/ - Search/List Nodes
# =============================================================================
@pytest.mark.asyncio
async def test_list_nodes_requires_auth(app_client: AsyncClient):
    response = await app_client.get(BASE_URL)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_nodes_with_invalid_token_returns_401(
    app_client: AsyncClient,
):
    headers = {'Authorization': 'Bearer invalid-token-here'}
    response = await app_client.get(BASE_URL, headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_nodes_returns_paginated_results(
    app_client: AsyncClient,
    test_user_root_node: Node,
    auth_headers: dict,
):
    response = await app_client.get(BASE_URL, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert 'page' in body
    assert 'results' in body
    assert isinstance(body['results'], list)


@pytest.mark.asyncio
async def test_list_nodes_with_query_param(
    app_client: AsyncClient,
    test_user_root_node: Node,
    auth_headers: dict,
):
    url = f'{BASE_URL}?query={test_user_root_node.title[:5]}'
    response = await app_client.get(url, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['page'] == 1
    assert len(body['results']) == 1


@pytest.mark.asyncio
async def test_list_nodes_with_pagination_params(
    app_client: AsyncClient,
    test_user_root_node: Node,
    auth_headers: dict,
):
    url = f'{BASE_URL}?page=2&size=5'
    response = await app_client.get(url, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['page'] == 2


# =============================================================================
# POST /api/v1/node/nodes/{id_}/add-child - Add Child Node
# =============================================================================
@pytest.mark.asyncio
async def test_add_child_requires_auth(app_client: AsyncClient, test_user_root_node: Node):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    data = {'title': 'Test Node', 'questions': 'What is this?', 'content': '{"root": {}}'}
    response = await app_client.post(url, json=data)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_child_creates_node(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    auth_headers: dict,
    faker: Faker,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    data = {'title': faker.name(), 'questions': faker.sentence(), 'content': '{"root": {}}'}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert 'id' in body

    new_node = await test_palace_node_manager.get(body['id'])
    assert new_node
    assert new_node.parent_pk == test_user_root_node.pk
    assert new_node.title == data['title']


@pytest.mark.asyncio
async def test_add_child_validates_required_fields(
    app_client: AsyncClient,
    test_user_root_node: Node,
    auth_headers: dict,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    data = {'content': '{"root": {}}'}
    response = await app_client.post(url, json=data, headers=auth_headers)
    error_details = response.json()['detail']
    assert response.status_code == 422
    assert len(error_details) == 2
    assert error_details[0]['loc'] == ['body', 'title']
    assert error_details[1]['loc'] == ['body', 'questions']


@pytest.mark.asyncio
async def test_add_child_sets_owner_id_from_token(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    test_user_context: UserTestContext,
    auth_headers: dict,
    faker: Faker,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    data = {'title': faker.name(), 'questions': faker.sentence(), 'content': '{"root": {}}'}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert 'id' in body

    new_node = await test_palace_node_manager.get(body['id'])
    assert new_node
    assert new_node.owner_id == str(test_user_context.sub)


@pytest.mark.asyncio
async def test_add_child_with_is_learn_false(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    auth_headers: dict,
    faker,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/add-child'
    data = {
        'title': faker.name(),
        'questions': faker.sentence(),
        'content': '{"root": {}}',
        'is_learn': False,
    }
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    new_node = await test_palace_node_manager.get(body['id'])
    assert new_node
    assert not new_node.is_learn


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_add_child_to_nonexistent_parent_returns_error(
    app_client: AsyncClient,
    auth_headers: dict,
    faker,
):
    url = f'{BASE_URL}nonexistent-id-12345/add-child'
    data = {'title': faker.name(), 'questions': faker.sentence(), 'content': '{"root": {}}'}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code in [404, 422, 500]


# =============================================================================
# GET /api/v1/node/nodes/{id_} - Get Node Detail
# =============================================================================
@pytest.mark.asyncio
async def test_get_node_requires_auth(app_client: AsyncClient):
    url = f'{BASE_URL}some_id'
    response = await app_client.get(url)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_nonexistent_node_returns_404(
    app_client: AsyncClient,
    auth_headers: dict,
):
    url = f'{BASE_URL}nonexistent_id_xyz'
    response = await app_client.get(url, headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_node_detail_returns_node(
    app_client: AsyncClient,
    test_user_root_node: Node,
    auth_headers: dict,
):
    url = f'{BASE_URL}{test_user_root_node.pk}'
    response = await app_client.get(url, headers=auth_headers)
    assert response.is_success
    response_data = response.json()
    assert response_data['id'] == test_user_root_node.pk


#
# # =============================================================================
# # GET /api/v1/node/nodes/{uid}/generate-content - Generate Content
# # =============================================================================
# @pytest.mark.asyncio
# async def test_generate_content_requires_valid_node(
#     app_client: AsyncClient,
# ):
#     url = f'{BASE}/nonexistent_id/generate-content'
#     response = await app_client.get(url)
#     assert response.status_code == 404
#
#
# @pytest.mark.asyncio
# @patch('minager.node.services.content_generation.HuggingFaceNodeContentGenerator.from_config')
# async def test_generate_content_calls_huggingface(
#     mock_from_config,
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     mock_generator = AsyncMock()
#     mock_generator.generate.return_value = '<p>Generated content</p>'
#     mock_from_config.return_value = mock_generator
#
#     url = f'{BASE}/{root_node.pk}/generate-content'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     assert response.text == '"<p>Generated content</p>"'
#     mock_generator.generate.assert_called_once()
#
#
# =============================================================================
# GET /api/v1/node/nodes/{uid}/children - Get Children
# =============================================================================
@pytest.mark.asyncio
async def test_get_children_returns_paginated_list(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    faker,
):
    # Create some children first
    for _ in range(3):
        await test_palace_node_manager.add_child(
            test_user_root_node.pk,
            {
                'title': faker.name(),
                'questions': faker.sentence(),
                'owner_id': 'test_owner',
                'content': '{"root": {}}',
                'order': 'aaaaa',
            },
        )

    url = f'{BASE_URL}{test_user_root_node.pk}/children'
    response = await app_client.get(url)
    assert response.status_code == 200
    body = response.json()
    assert 'results' in body
    assert 'page' in body
    assert len(body['results']) == 3


@pytest.mark.asyncio
async def test_get_children_empty_node(
    app_client: AsyncClient,
    test_user_root_node: Node,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/children'
    response = await app_client.get(url)
    assert response.status_code == 200
    body = response.json()
    assert body['results'] == []


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_get_children_nonexistent_node(app_client: AsyncClient):
    url = f'{BASE_URL}nonexistent_id/children'
    response = await app_client.get(url)
    assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# GET /api/v1/node/nodes/{uid}/statistics - Get Statistics
# =============================================================================
@pytest.mark.xfail
@pytest.mark.asyncio
async def test_get_statistics_returns_valid_structure(
    app_client: AsyncClient,
    test_user_root_node: Node,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/statistics'
    response = await app_client.get(url)
    assert response.status_code == 200
    body = response.json()
    assert 'indexes' in body
    assert 'subtree' in body
    assert 'node' in body


#
# @pytest.mark.asyncio
# async def test_get_statistics_nonexistent_node(
#     app_client: AsyncClient,
# ):
#     url = f'{BASE}/nonexistent_id/statistics'
#     response = await app_client.get(url)
#     # May raise error or return empty stats
#     assert response.status_code in [200, 404, 500]
#
#
# @pytest.mark.asyncio
# async def test_get_statistics_with_children(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
#     test_palace_node_manager: PalaceNodeManager,
#     faker,
# ):
#     # Create children with statistics
#     for _ in range(3):
#         await test_palace_node_manager.add_child(
#             root_node.pk,
#             {
#                 'title': faker.name(),
#                 'questions': faker.sentence(),
#                 'owner_id': 'test_owner',
#                 'content': '{"root": {"blocks": []}}',
#                 'order': 'aaaaa',
#                 'size': 10,
#                 'last_rating': 4,
#                 'repetitions': 2,
#             },
#         )
#
#     url = f'{BASE}/{root_node.pk}/statistics'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['subtree']['count'] >= 3
#
#
# # =============================================================================
# # GET /api/v1/node/nodes/{uid}/subtree - Get Subtree
# # =============================================================================
# @pytest.mark.asyncio
# async def test_get_subtree_returns_tree_structure(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
#     test_palace_node_manager: PalaceNodeManager,
#     faker,
# ):
#     # Create a small tree
#     child1 = await test_palace_node_manager.add_child(
#         root_node.pk,
#         {
#             'title': faker.name(),
#             'questions': faker.sentence(),
#             'owner_id': 'test_owner',
#             'content': '{"root": {}}',
#             'order': 'aaaaa',
#         },
#     )
#     await test_palace_node_manager.add_child(
#         child1.pk,
#         {
#             'title': faker.name(),
#             'questions': faker.sentence(),
#             'owner_id': 'test_owner',
#             'content': '{"root": {}}',
#             'order': 'aaaaa',
#         },
#     )
#
#     url = f'{BASE}/{root_node.pk}/subtree'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['id'] == root_node.pk
#     assert 'children' in body
#     assert len(body['children']) >= 1
#     # Check nested children
#     assert 'children' in body['children'][0]
#
#
# @pytest.mark.asyncio
# async def test_get_subtree_single_node(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     url = f'{BASE}/{root_node.pk}/subtree'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['id'] == root_node.pk
#     assert body['children'] == []
#
#
# @pytest.mark.asyncio
# async def test_get_subtree_nonexistent_node(
#     app_client: AsyncClient,
# ):
#     url = f'{BASE}/nonexistent_id/subtree'
#     response = await app_client.get(url)
#     # May return empty tree or error
#     assert response.status_code in [200, 404]
#


# =============================================================================
# GET /api/v1/node/nodes/{uid}/subtree/statistics - Get Subtree Statistics
# =============================================================================
@pytest.mark.asyncio
async def test_get_subtree_statistics_returns_valid_structure(
    app_client: AsyncClient,
    test_user_root_node: Node,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/subtree/statistics'
    response = await app_client.get(url)
    assert response.status_code == 200
    body = response.json()
    required_fields = [
        'count',
        'average_rating',
        'owner_views',
        'repetitions',
        'size',
        'outdated',
        'not_visited',
        'empty',
    ]
    for field in required_fields:
        assert field in body


@pytest.mark.asyncio
async def test_get_subtree_statistics_with_children(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    faker,
):
    # Create children
    for _ in range(3):
        await test_palace_node_manager.add_child(
            test_user_root_node.pk,
            {
                'title': faker.name(),
                'questions': faker.sentence(),
                'owner_id': 'test_owner',
                'content': '{"root": {}}',
                'order': 'aaaaa',
                'last_rating': 4,
            },
        )

    url = f'{BASE_URL}{test_user_root_node.pk}/subtree/statistics'
    response = await app_client.get(url)
    assert response.status_code == 200
    body = response.json()
    assert body['count'] >= 3


#
#
# @pytest.mark.asyncio
# async def test_get_subtree_statistics_single_node(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     url = f'{BASE}/{root_node.pk}/subtree/statistics'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['count'] == 1
#
#
# # =============================================================================
# # GET /api/v1/node/nodes/{uid}/subtree/ids - Get Subtree IDs
# # =============================================================================
# @pytest.mark.asyncio
# async def test_get_subtree_ids_returns_list(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
#     test_palace_node_manager: PalaceNodeManager,
#     faker,
# ):
#     # Create children
#     for _ in range(3):
#         await test_palace_node_manager.add_child(
#             root_node.pk,
#             {
#                 'title': faker.name(),
#                 'questions': faker.sentence(),
#                 'owner_id': 'test_owner',
#                 'content': '{"root": {}}',
#                 'order': 'aaaaa',
#             },
#         )
#
#     url = f'{BASE}/{root_node.pk}/subtree/ids'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     body = response.json()
#     assert isinstance(body, list)
#     assert len(body) >= 3
#
#
# @pytest.mark.asyncio
# async def test_get_subtree_ids_with_limit(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
#     test_palace_node_manager: PalaceNodeManager,
#     faker,
# ):
#     # Create children
#     for _ in range(10):
#         await test_palace_node_manager.add_child(
#             root_node.pk,
#             {
#                 'title': faker.name(),
#                 'questions': faker.sentence(),
#                 'owner_id': 'test_owner',
#                 'content': '{"root": {}}',
#                 'order': 'aaaaa',
#             },
#         )
#
#     url = f'{BASE}/{root_node.pk}/subtree/ids?limit=3'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     body = response.json()
#     assert isinstance(body, list)
#     assert len(body) <= 3
#
#
# @pytest.mark.asyncio
# async def test_get_subtree_ids_single_node(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     url = f'{BASE}/{root_node.pk}/subtree/ids'
#     response = await app_client.get(url)
#     assert response.status_code == 200
#     body = response.json()
#     assert isinstance(body, list)
#


# =============================================================================
# POST /api/v1/node/nodes/{uid}/move - Move Node
# =============================================================================
@pytest.mark.asyncio
async def test_move_node_as_last_child(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory,
    auth_headers: dict,
):
    # Create two children
    child1 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(),
    )
    child2 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(order='bbbbb'),
    )

    # Move child1 to be last child of child2
    url = f'{BASE_URL}{child1.pk}/move'
    data = {'target_id': child2.pk, 'position': MovePosition.last_child.value}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['title'] == child1.title


@pytest.mark.asyncio
async def test_move_node_as_first_child(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory,
    auth_headers: dict,
):
    child1 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(),
    )
    child2 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(order='bbbbb'),
    )

    url = f'{BASE_URL}{child2.pk}/move'
    data = {'target_id': child1.pk, 'position': MovePosition.first_child.value}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_move_node_before(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory,
    auth_headers: dict,
):
    child1 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(),
    )
    child2 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(order='bbbbb'),
    )

    url = f'{BASE_URL}{child2.pk}/move'
    data = {'target_id': child1.pk, 'position': MovePosition.before.value}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_move_node_after(
    app_client: AsyncClient,
    test_user_root_node: Node,
    test_palace_node_manager: PalaceNodeManager,
    node_create_data_factory,
    auth_headers: dict,
):
    child1 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(),
    )
    child2 = await test_palace_node_manager.add_child(
        test_user_root_node.pk,
        node_create_data_factory(order='bbbbb'),
    )

    url = f'{BASE_URL}{child1.pk}/move'
    data = {'target_id': child2.pk, 'position': MovePosition.after.value}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_move_node_invalid_position(
    app_client: AsyncClient,
    test_user_root_node: Node,
    auth_headers: dict,
):
    url = f'{BASE_URL}{test_user_root_node.pk}/move'
    data = {'target_id': 'some_target', 'position': 999}
    response = await app_client.post(url, json=data, headers=auth_headers)
    assert response.status_code in [422, 500]


# # =============================================================================
# # PATCH /api/v1/node/nodes/{uid} - Update Node
# # =============================================================================
# @pytest.mark.asyncio
# async def test_update_node_title(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
#     faker,
# ):
#     new_title = faker.name()
#     url = f'{BASE}/{root_node.pk}'
#     data = {'title': new_title}
#     response = await app_client.patch(url, json=data)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['title'] == new_title
#
#
# @pytest.mark.asyncio
# async def test_update_node_is_learn(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     url = f'{BASE}/{root_node.pk}'
#     data = {'is_learn': False}
#     response = await app_client.patch(url, json=data)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['is_learn'] is False
#
#
# @pytest.mark.asyncio
# async def test_update_node_content(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     new_content = '{"root": {"blocks": [{"type": "text", "data": "Updated"}]}}'
#     url = f'{BASE}/{root_node.pk}'
#     data = {'content': new_content}
#     response = await app_client.patch(url, json=data)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['content'] == new_content
#
#
# @pytest.mark.asyncio
# async def test_update_node_tags(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     url = f'{BASE}/{root_node.pk}'
#     data = {'tags': [10, 20, 30]}
#     response = await app_client.patch(url, json=data)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['tags'] == [10, 20, 30]
#
#
# @pytest.mark.asyncio
# async def test_update_node_statistics_fields(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
# ):
#     url = f'{BASE}/{root_node.pk}'
#     data = {
#         'last_rating': 5,
#         'repetitions': 3,
#         'difficulty': 3.5,
#         'owner_views': 10,
#     }
#     response = await app_client.patch(url, json=data)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['last_rating'] == 5
#     assert body['repetitions'] == 3
#
#
# @pytest.mark.asyncio
# async def test_update_node_partial_update(
#     app_client: AsyncClient,
#     test_user_root_node: Node,
#     faker: Faker,
# ):
#     """Only specified fields should be updated"""
#     url = f'{BASE_URL}{test_user_root_node.pk}'
#     data = {'title': faker.name()}
#     response = await app_client.patch(url, json=data)
#     assert response.status_code == 200
#     body = response.json()
#     assert body['title'] == data['title']
#     # Other fields should remain unchanged
#
#
# @pytest.mark.asyncio
# async def test_update_nonexistent_node(app_client: AsyncClient):
#     url = f'{BASE_URL}nonexistent_id'
#     data = {'title': 'New Title'}
#     response = await app_client.patch(url, json=data)
#     assert response.status_code in [404, 200, 500]


# # =============================================================================
# # DELETE /api/v1/node/nodes/{uid} - Delete Node
# # =============================================================================
# @pytest.mark.asyncio
# async def test_delete_node(
#     app_client: AsyncClient,
#     test_palace_node_manager: PalaceNodeManager,
#     faker,
# ):
#     # Create a node to delete
#     node = await test_palace_node_manager.create(
#         {
#             'title': faker.name(),
#             'questions': faker.sentence(),
#             'owner_id': 'test_owner',
#             'content': '{"root": {}}',
#             'order': 'aaaaaa',
#         }
#     )
#
#     url = f'{BASE}/{node.pk}'
#     response = await app_client.delete(url)
#     assert response.status_code == 200
#
#
# @pytest.mark.asyncio
# async def test_delete_node_with_children(
#     app_client: AsyncClient,
#     test_palace_node_manager: PalaceNodeManager,
#     faker,
# ):
#     # Create a node with children
#     parent = await test_palace_node_manager.create(
#         {
#             'title': faker.name(),
#             'questions': faker.sentence(),
#             'owner_id': 'test_owner',
#             'content': '{"root": {}}',
#             'order': 'aaaaaa',
#         }
#     )
#     await test_palace_node_manager.add_child(
#         parent.pk,
#         {
#             'title': faker.name(),
#             'questions': faker.sentence(),
#             'owner_id': 'test_owner',
#             'content': '{"root": {}}',
#             'order': 'aaaaa',
#         },
#     )
#     await test_palace_node_manager.add_child(
#         parent.pk,
#         {
#             'title': faker.name(),
#             'questions': faker.sentence(),
#             'owner_id': 'test_owner',
#             'content': '{"root": {}}',
#             'order': 'bbbbb',
#         },
#     )
#
#     url = f'{BASE}/{parent.pk}'
#     response = await app_client.delete(url)
#     # Should cascade delete children
#     assert response.status_code == 200
#
#
# @pytest.mark.asyncio
# async def test_delete_nonexistent_node(
#     app_client: AsyncClient,
# ):
#     url = f'{BASE}/nonexistent_id_xyz'
#     response = await app_client.delete(url)
#     # May return 200 (idempotent) or 404
#     assert response.status_code in [200, 404]
#
#
# # =============================================================================
# # Integration: Full Workflow Tests
# # =============================================================================
# @pytest.mark.asyncio
# async def test_full_node_lifecycle(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
#     auth_headers: dict,
#     faker,
# ):
#     """Test: Create -> Read -> Update -> Delete flow"""
#     # 1. Create child
#     create_url = f'{BASE}/{root_node.pk}/add-child'
#     create_data = {
#         'title': 'Lifecycle Test Node',
#         'questions': 'Test question',
#         'content': '{"root": {}}',
#     }
#     create_resp = await app_client.post(create_url, json=create_data, headers=auth_headers)
#     assert create_resp.status_code == 201
#     node_id = create_resp.json()['id']['id']
#
#     # 2. Read node
#     get_url = f'{BASE}/{node_id}'
#     get_resp = await app_client.get(get_url, headers=auth_headers)
#     assert get_resp.status_code == 200
#     assert get_resp.json()['title'] == 'Lifecycle Test Node'
#
#     # 3. Update node
#     update_url = f'{BASE}/{node_id}'
#     update_data = {'title': 'Updated Lifecycle Node'}
#     update_resp = await app_client.patch(update_url, json=update_data)
#     assert update_resp.status_code == 200
#     assert update_resp.json()['title'] == 'Updated Lifecycle Node'
#
#     # 4. Delete node
#     delete_url = f'{BASE}/{node_id}'
#     delete_resp = await app_client.delete(delete_url)
#     assert delete_resp.status_code == 200
#
#
# @pytest.mark.asyncio
# async def test_create_tree_and_verify_subtree(
#     app_client: AsyncClient,
#     root_node: NodeDetailSchema,
#     auth_headers: dict,
#     test_palace_node_manager: PalaceNodeManager,
#     faker,
# ):
#     """Create a 2-level tree and verify subtree endpoints"""
#     # Create children
#     child_ids = []
#     for _ in range(3):
#         child = await test_palace_node_manager.add_child(
#             root_node.pk,
#             {
#                 'title': faker.name(),
#                 'questions': faker.sentence(),
#                 'owner_id': 'test_owner',
#                 'content': '{"root": {}}',
#                 'order': 'aaaaa',
#             },
#         )
#         child_ids.append(child.pk)
#         # Add grandchild
#         await test_palace_node_manager.add_child(
#             child.pk,
#             {
#                 'title': faker.name(),
#                 'questions': faker.sentence(),
#                 'owner_id': 'test_owner',
#                 'content': '{"root": {}}',
#                 'order': 'aaaaa',
#             },
#         )
#
#     # Verify subtree structure
#     subtree_url = f'{BASE}/{root_node.pk}/subtree'
#     resp = await app_client.get(subtree_url)
#     assert resp.status_code == 200
#     tree = resp.json()
#     assert len(tree['children']) == 3
#     for child_node in tree['children']:
#         assert len(child_node['children']) >= 1
#
#     # Verify subtree IDs
#     ids_url = f'{BASE}/{root_node.pk}/subtree/ids'
#     resp = await app_client.get(ids_url)
#     assert resp.status_code == 200
#     ids = resp.json()
#     assert len(ids) >= 7  # root + 3 children + 3 grandchildren
#
#     # Verify subtree statistics
#     stats_url = f'{BASE}/{root_node.pk}/subtree/statistics'
#     resp = await app_client.get(stats_url)
#     assert resp.status_code == 200
#     stats = resp.json()
#     assert stats['count'] >= 7
