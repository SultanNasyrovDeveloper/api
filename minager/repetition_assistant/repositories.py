from datetime import UTC, datetime

from bson import ObjectId
from pymongo import ReturnDocument

from minager.core.db.mongodb import MongoDBRepository

from .models import AssistantReviewConversation, Message


class AssistantReviewConversationRepository(MongoDBRepository[AssistantReviewConversation]):
    COLLECTION = 'assistant_review_conversation'
    model_class = AssistantReviewConversation

    async def find_by_session_and_node(
        self, user_id: str, session_id: str, node_id: str
    ) -> AssistantReviewConversation | None:
        doc = await self.connection.find_one(
            {'user_id': user_id, 'session_id': session_id, 'node_id': node_id}
        )
        return self.model_class.model_validate(doc) if doc else None

    async def append_message(self, id_: str | ObjectId, message: Message) -> AssistantReviewConversation:
        id_ = id_ if isinstance(id_, ObjectId) else ObjectId(id_)
        updated = await self.connection.find_one_and_update(
            {'_id': id_},
            {
                '$push': {'messages': message.model_dump(mode='json')},
                '$set': {'updated': datetime.now(UTC)},
            },
            return_document=ReturnDocument.AFTER,
        )
        if updated is None:
            raise ValueError(f'{self.model_class.__name__}({id_}) not found')
        return self.model_class.model_validate(updated)
