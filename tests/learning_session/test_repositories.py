import pytest
from bson import ObjectId

from minager.learning_session.models import LearningSession
from minager.learning_session.repositories import LearningSessionRepository
from tests.conftest import UserTestContext

pytestmark = pytest.mark.asyncio


async def test_create_and_get(
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
):
    created = await test_learning_session_repository.create(
        {'user_id': str(test_user_context.sub), 'targets': ['some-node-id']}
    )
    assert created.id is not None

    fetched = await test_learning_session_repository.get(created.id)
    assert fetched.id == created.id
    assert fetched.user_id == str(test_user_context.sub)


async def test_get_returns_none_when_missing(test_learning_session_repository: LearningSessionRepository):
    result = await test_learning_session_repository.get(str(ObjectId()))
    assert result is None


async def test_find_active_for_user(
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
):
    await test_learning_session_repository.create(
        {'user_id': str(test_user_context.sub), 'targets': ['some-node-id'], 'is_active': True}
    )
    found = await test_learning_session_repository.find_active_for_user(str(test_user_context.sub))
    assert found is not None
    assert found.is_active is True


async def test_find_active_for_user_returns_none_when_no_active_session(
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
):
    result = await test_learning_session_repository.find_active_for_user(str(test_user_context.sub))
    assert result is None


async def test_update_modifies_and_returns_session(
    test_learning_session_repository: LearningSessionRepository,
    test_user_context: UserTestContext,
):
    created = await test_learning_session_repository.create(
        {'user_id': str(test_user_context.sub), 'targets': ['some-node-id']}
    )
    updated = await test_learning_session_repository.update(created.id, {'is_active': False})
    assert isinstance(updated, LearningSession)
    assert updated.is_active is False


async def test_update_raises_when_missing(test_learning_session_repository: LearningSessionRepository):
    with pytest.raises(ValueError):
        await test_learning_session_repository.update(str(ObjectId()), {'is_active': False})
