from fastapi import APIRouter, HTTPException, status

from minager.core.auth.dependencies import CurrentUserID

from . import dependencies, exceptions, schemas

router = APIRouter(prefix='/conversations')


@router.get('', response_model_by_alias=False)
async def find_conversation(
    session_id: str,
    node_id: str,
    user_id: CurrentUserID,
    service: dependencies.AssistantReviewConversationServiceDependency,
) -> schemas.AssistantReviewConversationSchema | None:
    return await service.find_by_session_and_node(
        user_id=str(user_id), session_id=session_id, node_id=node_id
    )


@router.post('', response_model_by_alias=False, status_code=status.HTTP_201_CREATED)
async def start_conversation(
    user_id: CurrentUserID,
    data: schemas.StartReviewConversationSchema,
    send_message_use_case: dependencies.SendMessageUseCaseDependency,
) -> schemas.AssistantReviewConversationSchema:
    return await send_message_use_case.execute(
        user_id=str(user_id),
        session_id=data.session_id,
        node_id=data.node_id,
        content=data.content,
    )


@router.post('/{id_}/messages', response_model_by_alias=False)
async def send_message(
    id_: str,
    user_id: CurrentUserID,
    data: schemas.SendMessageSchema,
    send_message_use_case: dependencies.SendMessageUseCaseDependency,
) -> schemas.AssistantReviewConversationSchema:
    try:
        return await send_message_use_case.execute(user_id=str(user_id), review_id=id_, content=data.content)
    except exceptions.ReviewNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
