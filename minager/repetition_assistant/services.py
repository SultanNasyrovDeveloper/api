from .models import AssistantReviewConversation
from .repositories import AssistantReviewConversationRepository


class AssistantReviewConversationService:
    def __init__(self, repository: AssistantReviewConversationRepository):
        self.repository = repository

    async def find_by_session_and_node(
        self, user_id: str, session_id: str, node_id: str
    ) -> AssistantReviewConversation | None:
        return await self.repository.find_by_session_and_node(
            user_id=user_id, session_id=session_id, node_id=node_id
        )
