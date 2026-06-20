from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest

from minager.learning_session.managers import LearningSessionManager
from minager.learning_session.models import LearningSession
from minager.node.managers import KnowledgeTreeNodeManager
from minager.node.models import Node
from tests.conftest import UserTestContext

pytestmark = pytest.mark.asyncio

BASE = '/api/v1/learning-session/learning-sessions'


# ---------------------------------------------------------------------------
# start()
# ---------------------------------------------------------------------------


async def test_start_creates_session(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_manager: KnowledgeTreeNodeManager,
    node_data_factory: Callable[..., dict],
):
    await test_palace_node_manager.add_child(test_user_root_node.pk, node_data_factory())
    session = await test_learning_session_manager.start(
        user_id=str(test_user_context.sub),
        data={'targets': [test_user_root_node.id.id]},
    )
    assert isinstance(session, LearningSession)
    assert session.id is not None
    assert session.is_active is True
    assert session.user_id == str(test_user_context.sub)
    assert session.current_node is not None


async def test_start_returns_existing_active_session(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    second = await test_learning_session_manager.start(
        user_id=str(test_user_context.sub),
        data={'targets': active_session.targets},
    )
    assert second.id == active_session.id


async def test_start_replaces_expired_session(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
    await test_learning_session_manager.update(active_session.id, {'last_activity_datetime': two_hours_ago})

    new_session = await test_learning_session_manager.start(
        user_id=str(test_user_context.sub),
        data={'targets': active_session.targets},
    )
    assert new_session.id != active_session.id
    assert new_session.is_active is True

    old_session = await test_learning_session_manager.get(active_session.id)
    assert old_session.is_active is False


# ---------------------------------------------------------------------------
# get_my_active_session()
# ---------------------------------------------------------------------------


async def test_get_my_active_session_returns_session(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    result = await test_learning_session_manager.get_my_active_session(str(test_user_context.sub))
    assert result is not None
    assert result.id == active_session.id


async def test_get_my_active_session_returns_none_when_no_session(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
):
    result = await test_learning_session_manager.get_my_active_session(str(test_user_context.sub))
    assert result is None


async def test_get_my_active_session_finishes_expired_session(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
    await test_learning_session_manager.update(active_session.id, {'last_activity_datetime': two_hours_ago})

    result = await test_learning_session_manager.get_my_active_session(str(test_user_context.sub))
    assert result is None

    finished = await test_learning_session_manager.get(active_session.id)
    assert finished.is_active is False


# ---------------------------------------------------------------------------
# perform_repetition()
# ---------------------------------------------------------------------------


async def test_perform_repetition_good_rating_advances_queue(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    previous_node = active_session.current_node
    previous_queue_len = len(active_session.queue)

    updated = await test_learning_session_manager.perform_repetition(
        session_id=active_session.id,
        node_id=active_session.current_node,
        rating=4,
        user_id=str(test_user_context.sub),
    )

    assert updated.current_node != previous_node or updated.current_node is None
    assert len(updated.queue) == previous_queue_len - 1


async def test_perform_repetition_bad_rating_adds_to_bad_queue(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    updated = await test_learning_session_manager.perform_repetition(
        session_id=active_session.id,
        node_id=active_session.current_node,
        rating=1,
        user_id=str(test_user_context.sub),
    )
    assert active_session.current_node in updated.bad_repetition_queue


async def test_perform_repetition_switches_to_bad_queue_when_main_empty(
    test_learning_session_manager: LearningSessionManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    # Rate current node badly to populate bad_repetition_queue
    after_bad = await test_learning_session_manager.perform_repetition(
        session_id=active_session.id,
        node_id=active_session.current_node,
        rating=1,
        user_id=str(test_user_context.sub),
    )
    bad_node = after_bad.bad_repetition_queue[0]

    # Keep rating good until the bad_repetition_queue is exhausted (the switch
    # happens when we rate the last main-queue node — one iteration beyond when
    # queue becomes empty, which is why we loop on bad_repetition_queue).
    session = after_bad
    while session.bad_repetition_queue:
        session = await test_learning_session_manager.perform_repetition(
            session_id=session.id,
            node_id=session.current_node,
            rating=4,
            user_id=str(test_user_context.sub),
        )

    assert session.current_node == bad_node
    assert session.bad_repetition_queue == []


async def test_perform_repetition_updates_node_in_surreal(
    test_learning_session_manager: LearningSessionManager,
    test_palace_node_manager: KnowledgeTreeNodeManager,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    node_id = active_session.current_node
    before = await test_palace_node_manager.get(node_id)
    before_repetitions = before.repetitions or 0

    await test_learning_session_manager.perform_repetition(
        session_id=active_session.id,
        node_id=node_id,
        rating=4,
        user_id=str(test_user_context.sub),
    )

    after = await test_palace_node_manager.get(node_id)
    assert after.repetitions == before_repetitions + 1
    assert after.last_repetition is not None


# ---------------------------------------------------------------------------
# finish()
# ---------------------------------------------------------------------------


async def test_finish_marks_session_inactive(
    test_learning_session_manager: LearningSessionManager,
    active_session: LearningSession,
):
    finished = await test_learning_session_manager.finish(active_session.id)
    assert finished.is_active is False
    assert finished.current_node is None
    assert finished.queue == []


# ---------------------------------------------------------------------------
# regenerate_queue()
# ---------------------------------------------------------------------------


async def test_regenerate_queue_resets_current_node(
    test_learning_session_manager: LearningSessionManager,
    active_session: LearningSession,
):
    updated = await test_learning_session_manager.regenerate_queue(active_session.id)
    assert updated.current_node is not None
