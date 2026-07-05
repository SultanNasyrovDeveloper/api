from datetime import UTC, datetime, timedelta

import pytest
from bson import ObjectId

from minager.learning_session.exceptions import SessionNotFoundError
from minager.learning_session.models import LearningSession
from minager.learning_session.repositories import LearningSessionRepository
from minager.learning_session.services import LearningSessionService
from tests.conftest import UserTestContext

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# get_my_active_session()
# ---------------------------------------------------------------------------


async def test_get_my_active_session_returns_session(
    test_learning_session_service: LearningSessionService,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    result = await test_learning_session_service.get_my_active_session(str(test_user_context.sub))
    assert result is not None
    assert result.id == active_session.id


async def test_get_my_active_session_returns_none_when_no_session(
    test_learning_session_service: LearningSessionService,
    test_user_context: UserTestContext,
):
    result = await test_learning_session_service.get_my_active_session(str(test_user_context.sub))
    assert result is None


async def test_get_my_active_session_finishes_expired_session(
    test_learning_session_service: LearningSessionService,
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
    active_session: LearningSession,
):
    two_hours_ago = datetime.now(UTC) - timedelta(hours=2)
    await test_learning_session_repository.update(
        active_session.id, {'last_activity_datetime': two_hours_ago}
    )

    result = await test_learning_session_service.get_my_active_session(str(test_user_context.sub))
    assert result is None

    finished = await test_learning_session_repository.get(active_session.id)
    assert finished.is_active is False


# ---------------------------------------------------------------------------
# finish()
# ---------------------------------------------------------------------------


async def test_finish_marks_session_inactive(
    test_learning_session_service: LearningSessionService,
    active_session: LearningSession,
):
    finished = await test_learning_session_service.finish(active_session.id)
    assert finished.is_active is False
    assert finished.current_node is None
    assert finished.queue == []


async def test_finish_raises_when_session_missing(
    test_learning_session_service: LearningSessionService,
):
    with pytest.raises(SessionNotFoundError):
        await test_learning_session_service.finish(str(ObjectId()))
