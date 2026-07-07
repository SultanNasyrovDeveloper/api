from minager.core.db.mongodb import MongoDBRepository

from .models import LearningSession


class LearningSessionRepository(MongoDBRepository[LearningSession]):
    COLLECTION = 'session'
    model_class = LearningSession

    async def find_active_for_user(self, user_id: str) -> LearningSession | None:
        session_data = await self.connection.find_one({'user_id': user_id, 'is_active': True})
        return LearningSession.model_validate(session_data) if session_data else None
