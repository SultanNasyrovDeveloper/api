from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId
from surorm.data_model import Datetime

from minager.core.clients.knowledge_tree import SubtreeFilter, TraversalOrder
from minager.learning_session.exceptions import EmptyQueueError, SessionNotFoundError
from minager.learning_session.models import LearningSession
from minager.learning_session.repositories import LearningSessionRepository
from minager.learning_session.schemas import StartLearningSessionSchema
from minager.learning_session.use_cases import (
    PerformRepetitionUseCase,
    RegenerateQueueUseCase,
    StartSessionUseCase,
)
from minager.node.models import Node
from minager.node.repositories import NodeRepository
from minager.node.services import NodeService
from tests.conftest import UserTestContext

pytestmark = pytest.mark.asyncio


async def test_start_creates_session(
    test_start_session_use_case: StartSessionUseCase,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
):
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(targets=[test_user_root_node.id.id_]),
    )
    assert isinstance(session, LearningSession)
    assert session.id is not None
    assert session.is_active is True
    assert session.user_id == str(test_user_context.sub)
    assert session.current_node is not None


async def test_start_defaults_to_all_nodes_in_random_order(
    test_start_session_use_case: StartSessionUseCase,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
):
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(targets=[test_user_root_node.id.id_]),
    )
    assert session.filter_strategy is SubtreeFilter.all
    assert session.traversal_order is TraversalOrder.random


async def test_start_persists_the_requested_strategies(
    test_start_session_use_case: StartSessionUseCase,
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
):
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(
            targets=[test_user_root_node.id.id_],
            filter_strategy=SubtreeFilter.never_reviewed,
            traversal_order=TraversalOrder.bfs,
        ),
    )

    # Re-read through the repository: the strategies must survive the Mongo round trip,
    # not merely live on the in-memory model the use case returned.
    reloaded = await test_learning_session_repository.get(session.id)
    assert reloaded.filter_strategy is SubtreeFilter.never_reviewed
    assert reloaded.traversal_order is TraversalOrder.bfs


async def test_start_filter_narrows_the_queue_to_matching_nodes(
    test_start_session_use_case: StartSessionUseCase,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
):
    overdue = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) - timedelta(days=1))),
    )
    not_yet_due = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) + timedelta(days=1))),
    )

    session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(
            targets=[test_user_root_node.id.id_],
            filter_strategy=SubtreeFilter.due,
            traversal_order=TraversalOrder.bfs,
        ),
    )

    queued = {session.current_node, *session.queue}
    assert overdue.pk in queued
    assert not_yet_due.pk not in queued


async def test_start_traversal_order_due_first_puts_the_most_overdue_node_first(
    test_start_session_use_case: StartSessionUseCase,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
):
    most_overdue = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) - timedelta(days=30))),
    )
    await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) - timedelta(days=1))),
    )

    session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(
            targets=[test_user_root_node.id.id_],
            filter_strategy=SubtreeFilter.due,
            traversal_order=TraversalOrder.due_first,
        ),
    )
    assert session.current_node == most_overdue.pk


async def test_start_raises_when_no_node_matches_the_filter(
    test_start_session_use_case: StartSessionUseCase,
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
):
    # Fresh nodes default next_optimal_repetition to now + 1 day, so nothing is ever due.
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())

    with pytest.raises(EmptyQueueError):
        await test_start_session_use_case.execute(
            user_id=str(test_user_context.sub),
            data=StartLearningSessionSchema(
                targets=[test_user_root_node.id.id_],
                filter_strategy=SubtreeFilter.due,
            ),
        )

    # The whole point of raising before save: no dead session is left behind to block
    # the next `start` call.
    assert await test_learning_session_repository.find_active_for_user(str(test_user_context.sub)) is None


async def test_start_after_an_empty_filter_result_still_works(
    test_start_session_use_case: StartSessionUseCase,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
):
    await test_palace_node_service.add_child(test_user_root_node.pk, node_data_factory())
    with pytest.raises(EmptyQueueError):
        await test_start_session_use_case.execute(
            user_id=str(test_user_context.sub),
            data=StartLearningSessionSchema(
                targets=[test_user_root_node.id.id_], filter_strategy=SubtreeFilter.due
            ),
        )

    session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(
            targets=[test_user_root_node.id.id_], filter_strategy=SubtreeFilter.all
        ),
    )
    assert session.current_node is not None


async def test_start_rejects_a_traversal_order_with_no_query_behind_it(
    test_start_session_use_case: StartSessionUseCase,
    test_user_context: UserTestContext,
    test_user_root_node: Node,
):
    with pytest.raises(AssertionError):
        await test_start_session_use_case.execute(
            user_id=str(test_user_context.sub),
            data=StartLearningSessionSchema(
                targets=[test_user_root_node.id.id_],
                traversal_order=TraversalOrder.dfs,
            ),
        )


async def test_regenerate_queue_reuses_the_sessions_stored_strategies(
    test_regenerate_queue_use_case: RegenerateQueueUseCase,
    test_learning_session_repository: LearningSessionRepository,
    test_user_root_node: Node,
    test_palace_node_service: NodeService,
    node_data_factory: Callable[..., dict],
    active_session: LearningSession,
):
    not_yet_due = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) + timedelta(days=1))),
    )
    overdue = await test_palace_node_service.add_child(
        test_user_root_node.pk,
        node_data_factory(next_optimal_repetition=Datetime(datetime.now(UTC) - timedelta(days=1))),
    )
    await test_learning_session_repository.update(
        active_session.id,
        {'filter_strategy': SubtreeFilter.due, 'traversal_order': TraversalOrder.bfs},
    )

    updated = await test_regenerate_queue_use_case.execute(active_session.id)

    queued = {updated.current_node, *updated.queue}
    assert overdue.pk in queued
    assert not_yet_due.pk not in queued


async def test_start_returns_existing_active_session(
    test_start_session_use_case: StartSessionUseCase,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    second = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(targets=active_session.targets),
    )
    assert second.id == active_session.id


async def test_start_replaces_expired_session(
    test_start_session_use_case: StartSessionUseCase,
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
    await test_learning_session_repository.update(
        active_session.id, {'last_activity_datetime': two_hours_ago}
    )

    new_session = await test_start_session_use_case.execute(
        user_id=str(test_user_context.sub),
        data=StartLearningSessionSchema(targets=active_session.targets),
    )
    assert new_session.id != active_session.id
    assert new_session.is_active is True

    old_session = await test_learning_session_repository.get(active_session.id)
    assert old_session.is_active is False


async def test_regenerate_queue_resets_current_node(
    test_regenerate_queue_use_case: RegenerateQueueUseCase,
    active_session: LearningSession,
):
    updated = await test_regenerate_queue_use_case.execute(active_session.id)
    assert updated.current_node is not None


async def test_regenerate_queue_raises_when_session_missing(
    test_regenerate_queue_use_case: RegenerateQueueUseCase,
):
    with pytest.raises(SessionNotFoundError):
        await test_regenerate_queue_use_case.execute(str(ObjectId()))


async def test_perform_repetition_good_rating_advances_queue(
    test_perform_repetition_use_case: PerformRepetitionUseCase,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    previous_node = active_session.current_node
    previous_queue_len = len(active_session.queue)

    updated = await test_perform_repetition_use_case.execute(
        session_id=active_session.id,
        node_id=active_session.current_node,
        rating=4,
        user_id=str(test_user_context.sub),
    )

    assert updated.current_node != previous_node or updated.current_node is None
    assert len(updated.queue) == previous_queue_len - 1


async def test_perform_repetition_bad_rating_adds_to_bad_queue(
    test_perform_repetition_use_case: PerformRepetitionUseCase,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    updated = await test_perform_repetition_use_case.execute(
        session_id=active_session.id,
        node_id=active_session.current_node,
        rating=1,
        user_id=str(test_user_context.sub),
    )
    assert active_session.current_node in updated.bad_repetition_queue


async def test_perform_repetition_switches_to_bad_queue_when_main_empty(
    test_perform_repetition_use_case: PerformRepetitionUseCase,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    # Rate current node badly to populate bad_repetition_queue
    after_bad = await test_perform_repetition_use_case.execute(
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
        session = await test_perform_repetition_use_case.execute(
            session_id=session.id,
            node_id=session.current_node,
            rating=4,
            user_id=str(test_user_context.sub),
        )

    assert session.current_node == bad_node
    assert session.bad_repetition_queue == []


async def test_perform_repetition_updates_node_in_surreal(
    test_perform_repetition_use_case: PerformRepetitionUseCase,
    test_palace_node_repository: NodeRepository,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    node_id = active_session.current_node
    before = await test_palace_node_repository.get(node_id)
    before_repetitions = before.repetitions or 0

    await test_perform_repetition_use_case.execute(
        session_id=active_session.id,
        node_id=node_id,
        rating=4,
        user_id=str(test_user_context.sub),
    )

    after = await test_palace_node_repository.get(node_id)
    assert after.repetitions == before_repetitions + 1
    assert after.last_repetition is not None


async def test_perform_repetition_raises_when_session_missing(
    test_perform_repetition_use_case: PerformRepetitionUseCase,
    test_user_context: UserTestContext,
):
    with pytest.raises(SessionNotFoundError):
        await test_perform_repetition_use_case.execute(
            session_id=str(ObjectId()),
            node_id='irrelevant-node-id',
            rating=4,
            user_id=str(test_user_context.sub),
        )


async def test_perform_repetition_raises_when_session_belongs_to_another_user(
    test_perform_repetition_use_case: PerformRepetitionUseCase,
    active_session: LearningSession,
):
    with pytest.raises(SessionNotFoundError):
        await test_perform_repetition_use_case.execute(
            session_id=active_session.id,
            node_id=active_session.current_node,
            rating=4,
            user_id='some-other-user-id',
        )
