import pytest
from httpx import AsyncClient

from minager.learning_session.models import LearningSession
from minager.learning_session.repositories import LearningSessionRepository
from minager.node.managers import KnowledgeTreeNodeManager
from minager.node.models import Node

pytestmark = pytest.mark.asyncio

BASE = '/api/v1/learning-session/learning-sessions'


# ---------------------------------------------------------------------------
# GET /active
# ---------------------------------------------------------------------------


async def test_get_active_session_returns_null_when_none(
    app_client: AsyncClient,
    auth_headers: dict,
):
    response = await app_client.get(f'{BASE}/active', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() is None


async def test_get_active_session_returns_existing(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    response = await app_client.get(f'{BASE}/active', headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body['id'] == str(active_session.id)


async def test_get_active_session_excludes_queue_field(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    response = await app_client.get(f'{BASE}/active', headers=auth_headers)
    assert 'queue' not in response.json()


async def test_get_active_session_requires_auth(app_client: AsyncClient):
    response = await app_client.get(f'{BASE}/active')
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /start
# ---------------------------------------------------------------------------


async def test_start_session_creates_session(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_data_factory,
):
    await test_palace_node_manager.add_child(test_user_root_node.pk, node_data_factory())
    payload = {'targets': [test_user_root_node.id.id]}
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body['is_active'] is True
    assert body['current_node'] is not None
    assert 'queue' not in body


async def test_start_session_returns_existing_if_active(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    payload = {'targets': active_session.targets}
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 201
    assert response.json()['id'] == str(active_session.id)


async def test_start_session_requires_auth(
    app_client: AsyncClient,
    test_user_root_node: Node,
):
    response = await app_client.post(f'{BASE}/start', json={'targets': [test_user_root_node.id.id]})
    assert response.status_code in (401, 403)


# ---------------------------------------------------------------------------
# POST /{id}/repeat
# ---------------------------------------------------------------------------


async def test_perform_repetition_good_rating(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    payload = {'node_id': active_session.current_node, 'rating': 4}
    response = await app_client.post(f'{BASE}/{active_session.id}/repeat', json=payload, headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['current_node'] != active_session.current_node or body['current_node'] is None
    assert 'queue' not in body


async def test_perform_repetition_bad_rating_populates_bad_queue(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
    test_learning_session_repository: LearningSessionRepository,
):
    rated_node = active_session.current_node
    payload = {'node_id': rated_node, 'rating': 1}
    response = await app_client.post(f'{BASE}/{active_session.id}/repeat', json=payload, headers=auth_headers)
    assert response.status_code == 200

    # Verify via repository (queue excluded from API response)
    session = await test_learning_session_repository.get(active_session.id)
    assert rated_node in session.bad_repetition_queue


async def test_perform_repetition_response_excludes_queue(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    payload = {'node_id': active_session.current_node, 'rating': 3}
    response = await app_client.post(f'{BASE}/{active_session.id}/repeat', json=payload, headers=auth_headers)
    assert 'queue' not in response.json()


async def test_perform_repetition_invalid_rating_rejected(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    payload = {'node_id': active_session.current_node, 'rating': 99}
    response = await app_client.post(f'{BASE}/{active_session.id}/repeat', json=payload, headers=auth_headers)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /{id}/generate-queue
# ---------------------------------------------------------------------------


async def test_regenerate_queue(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    response = await app_client.post(f'{BASE}/{active_session.id}/generate-queue', headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['current_node'] is not None
    assert 'queue' not in body


# ---------------------------------------------------------------------------
# POST /{id}/finish
# ---------------------------------------------------------------------------


async def test_finish_session(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    response = await app_client.post(f'{BASE}/{active_session.id}/finish', headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body['is_active'] is False
    assert body['current_node'] is None


async def test_get_active_returns_null_after_finish(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
):
    await app_client.post(f'{BASE}/{active_session.id}/finish', headers=auth_headers)
    response = await app_client.get(f'{BASE}/active', headers=auth_headers)
    assert response.status_code == 200
    assert response.json() is None
