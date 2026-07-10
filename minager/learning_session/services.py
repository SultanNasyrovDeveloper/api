from datetime import UTC, datetime

from . import exceptions
from .models import LearningSession
from .repositories import LearningSessionRepository


class LearningSessionService:
    def __init__(self, repository: LearningSessionRepository):
        self.repository = repository

    async def get(self, id_: str) -> LearningSession:
        session = await self.repository.get(id_)
        if not session:
            raise exceptions.SessionNotFoundError
        return session

    async def get_my_active_session(self, user_id: str) -> LearningSession | None:
        session = await self.repository.find_active_for_user(user_id)
        if not session:
            return None
        if session.is_expired:
            await self.finish(session.id)
            return None
        return session

    async def finish(self, id_: str) -> LearningSession:
        try:
            return await self.repository.update(
                id_,
                {
                    'is_active': False,
                    'finish_datetime': datetime.now(UTC),
                    'current_node': None,
                    'queue': [],
                    'bad_repetition_queue': [],
                },
            )
        except ValueError:
            raise exceptions.SessionNotFoundError from None
