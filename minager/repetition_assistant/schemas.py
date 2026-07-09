from pydantic import BaseModel, Field

from .models import AssistantReviewConversation


class StartReviewConversationSchema(BaseModel):
    session_id: str = Field(description='ID of the learning session the review belongs to')
    node_id: str = Field(description='ID of the node being reviewed')
    content: str = Field(min_length=1, description='The user message text')


class SendMessageSchema(BaseModel):
    content: str = Field(min_length=1, description='The user message text')


AssistantReviewConversationSchema = AssistantReviewConversation
