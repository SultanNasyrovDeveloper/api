from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from surorm.data_model import Datetime

from minager.learning_session.models import LearningSession
from minager.learning_session.repositories import LearningSessionRepository
from minager.node.models import Node
from minager.node.services import NodeService

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
    test_palace_node_service: NodeService,
    node_data_factory,
):
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    payload = {'targets': [test_user_root_node.id.id_]}
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
    response = await app_client.post(f'{BASE}/start', json={'targets': [test_user_root_node.id.id_]})
    assert response.status_code in (401, 403)


async def test_start_session_defaults_strategies_when_omitted(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory,
):
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    payload = {'targets': [test_user_root_node.id.id_]}
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body['filter_strategy'] == 'all'
    assert body['traversal_order'] == 'random'


async def test_start_session_accepts_and_echoes_strategies(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory,
):
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    payload = {
        'targets': [test_user_root_node.id.id_],
        'filter_strategy': 'never_reviewed',
        'traversal_order': 'bfs',
    }
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body['filter_strategy'] == 'never_reviewed'
    assert body['traversal_order'] == 'bfs'


async def test_start_session_filter_narrows_the_queue(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    test_learning_session_repository: LearningSessionRepository,
    node_data_factory,
):
    overdue = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) - timedelta(days=1))),
    )
    not_yet_due = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) + timedelta(days=1))),
    )
    payload = {
        'targets': [test_user_root_node.id.id_],
        'filter_strategy': 'due',
        'traversal_order': 'bfs',
    }
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 201

    # The queue is excluded from the response, so read it back through the repository.
    session = await test_learning_session_repository.get(response.json()['id'])
    queued = {session.current_node, *session.queue}
    assert overdue.pk in queued
    assert not_yet_due.pk not in queued


async def test_start_session_returns_400_when_no_node_matches_the_filter(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory,
):
    # Fresh nodes are scheduled a day out, so a `due` session matches nothing.
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    payload = {'targets': [test_user_root_node.id.id_], 'filter_strategy': 'due'}
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 400


async def test_start_session_with_empty_filter_result_does_not_block_later_starts(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory,
):
    """A rejected `due` start must not persist a nodeless active session.

    If it did, every later `start` would short-circuit onto that dead session and the
    user could not study anything until it expired an hour later.
    """
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    targets = [test_user_root_node.id.id_]

    rejected = await app_client.post(
        f'{BASE}/start', json={'targets': targets, 'filter_strategy': 'due'}, headers=auth_headers
    )
    assert rejected.status_code == 400

    # No active session should have been left behind.
    active = await app_client.get(f'{BASE}/active', headers=auth_headers)
    assert active.json() is None

    accepted = await app_client.post(
        f'{BASE}/start', json={'targets': targets, 'filter_strategy': 'all'}, headers=auth_headers
    )
    assert accepted.status_code == 201
    assert accepted.json()['current_node'] is not None


async def test_start_session_rejects_unknown_strategy_value(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
):
    payload = {'targets': [test_user_root_node.id.id_], 'filter_strategy': 'not_a_real_filter'}
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 422


async def test_start_session_rejects_traversal_order_with_no_query_behind_it(
    app_client: AsyncClient,
    auth_headers: dict,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory,
):
    """`dfs` is a declared TraversalOrder that no query implements yet.

    It passes schema validation, so the failure surfaces from the knowledge tree as an
    AssertionError. The endpoint must translate that into a 422, not leak a 500.
    """
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    payload = {'targets': [test_user_root_node.id.id_], 'traversal_order': 'dfs'}
    response = await app_client.post(f'{BASE}/start', json=payload, headers=auth_headers)
    assert response.status_code == 422


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


async def test_regenerate_queue_applies_the_sessions_stored_filter(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    test_learning_session_repository: LearningSessionRepository,
    node_data_factory,
):
    overdue = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) - timedelta(days=1))),
    )
    not_yet_due = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) + timedelta(days=1))),
    )
    await test_learning_session_repository.update(
        active_session.id, {'filter_strategy': 'due', 'traversal_order': 'bfs'}
    )

    response = await app_client.post(f'{BASE}/{active_session.id}/generate-queue', headers=auth_headers)
    assert response.status_code == 200

    session = await test_learning_session_repository.get(active_session.id)
    queued = {session.current_node, *session.queue}
    assert overdue.pk in queued
    assert not_yet_due.pk not in queued


async def test_regenerate_queue_rejects_stored_traversal_order_with_no_query(
    app_client: AsyncClient,
    auth_headers: dict,
    active_session: LearningSession,
    test_learning_session_repository: LearningSessionRepository,
):
    await test_learning_session_repository.update(active_session.id, {'traversal_order': 'dfs'})

    response = await app_client.post(f'{BASE}/{active_session.id}/generate-queue', headers=auth_headers)
    assert response.status_code == 422


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
