import pytest
from bson import ObjectId
from httpx import AsyncClient

from minager.node.models import Node

pytestmark = pytest.mark.asyncio

BASE = '/api/v1/repetition-assistant/conversations'
SESSION_ID = 'session:1'


async def test_start_review_creates_conversation(
    app_client: AsyncClient,
    auth_headers: dict,
    review_node: Node,
):
    payload = {'session_id': SESSION_ID, 'node_id': review_node.pk, 'content': 'I think it is a tree.'}
    response = await app_client.post(BASE, json=payload, headers=auth_headers)

    assert response.status_code == 201
    body = response.json()
    assert body['id'] is not None
    assert body['session_id'] == SESSION_ID
    assert body['node_id'] == review_node.pk
    roles = [m['role'] for m in body['messages']]
    assert roles == ['user', 'assistant']


async def test_start_review_requires_auth(
    app_client: AsyncClient,
    review_node: Node,
):
    response = await app_client.post(
        BASE, json={'session_id': SESSION_ID, 'node_id': review_node.pk, 'content': 'hi'}
    )
    assert response.status_code in (401, 403)


async def test_start_review_rejects_empty_content(
    app_client: AsyncClient,
    auth_headers: dict,
    review_node: Node,
):
    response = await app_client.post(
        BASE,
        json={'session_id': SESSION_ID, 'node_id': review_node.pk, 'content': ''},
        headers=auth_headers,
    )
    assert response.status_code == 422


async def test_start_review_requires_session_id(
    app_client: AsyncClient,
    auth_headers: dict,
    review_node: Node,
):
    response = await app_client.post(
        BASE, json={'node_id': review_node.pk, 'content': 'hi'}, headers=auth_headers
    )
    assert response.status_code == 422


async def test_send_message_appends_turn(
    app_client: AsyncClient,
    auth_headers: dict,
    review_node: Node,
):
    created = await app_client.post(
        BASE,
        json={'session_id': SESSION_ID, 'node_id': review_node.pk, 'content': 'first'},
        headers=auth_headers,
    )
    review_id = created.json()['id']

    response = await app_client.post(
        f'{BASE}/{review_id}/messages', json={'content': 'second'}, headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body['id'] == review_id
    roles = [m['role'] for m in body['messages']]
    assert roles == ['user', 'assistant', 'user', 'assistant']


async def test_send_message_returns_404_when_review_missing(
    app_client: AsyncClient,
    auth_headers: dict,
):
    response = await app_client.post(
        f'{BASE}/{ObjectId()}/messages', json={'content': 'hi'}, headers=auth_headers
    )
    assert response.status_code == 404


async def test_send_message_requires_auth(
    app_client: AsyncClient,
):
    response = await app_client.post(f'{BASE}/{ObjectId()}/messages', json={'content': 'hi'})
    assert response.status_code in (401, 403)


async def test_find_conversation_returns_history_for_session_and_node(
    app_client: AsyncClient,
    auth_headers: dict,
    review_node: Node,
):
    created = await app_client.post(
        BASE,
        json={'session_id': SESSION_ID, 'node_id': review_node.pk, 'content': 'first'},
        headers=auth_headers,
    )
    review_id = created.json()['id']

    response = await app_client.get(
        BASE, params={'session_id': SESSION_ID, 'node_id': review_node.pk}, headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body['id'] == review_id
    assert body['session_id'] == SESSION_ID
    assert body['node_id'] == review_node.pk
    assert [m['role'] for m in body['messages']] == ['user', 'assistant']


async def test_find_conversation_returns_null_when_none(
    app_client: AsyncClient,
    auth_headers: dict,
    review_node: Node,
):
    response = await app_client.get(
        BASE, params={'session_id': 'session:other', 'node_id': review_node.pk}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() is None


async def test_find_conversation_hidden_from_other_users(
    app_client: AsyncClient,
    auth_headers: dict,
    other_user_auth_headers: dict,
    review_node: Node,
):
    await app_client.post(
        BASE,
        json={'session_id': SESSION_ID, 'node_id': review_node.pk, 'content': 'first'},
        headers=auth_headers,
    )

    response = await app_client.get(
        BASE,
        params={'session_id': SESSION_ID, 'node_id': review_node.pk},
        headers=other_user_auth_headers,
    )
    assert response.status_code == 200
    assert response.json() is None


async def test_find_conversation_requires_auth(
    app_client: AsyncClient,
    review_node: Node,
):
    response = await app_client.get(BASE, params={'session_id': SESSION_ID, 'node_id': review_node.pk})
    assert response.status_code in (401, 403)
