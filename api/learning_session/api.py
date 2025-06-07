from typing import Optional

from fastapi import APIRouter, status

from api.core.api.dependencies import App, RequestUser

from . import schemas

router = APIRouter(prefix='/sessions')


@router.get(
    '/my-active-session',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def get_my_active_session(
    user: RequestUser, app: App
) -> Optional[schemas.LearningSessionSchema]:
    return await app.state.learning_session.get_my_active_session(user['sub'])


@router.post(
    '/start',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
    status_code=status.HTTP_201_CREATED,
)
async def start(
    learning_session: schemas.StartLearningSessionSchema, app: App, user: RequestUser
) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.start(
        user_id=user['sub'], data=learning_session.model_dump(mode='json')
    )


@router.post(
    '/{id_}/regenerate-queue',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def regenerate_queue(id_: str, app: App) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.regenerate_queue(id_)


@router.post(
    '/{id_}/record-repetition',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def record_repetition(
    id_: str,
    user: RequestUser,
    repetition_data: schemas.RecordRepetitionDataSchema,
    app: App,
) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.record_repetition(
        session_id=id_, user_id=user['sub'], **repetition_data.model_dump()
    )


@router.post('/{id_}/finish', response_model_by_alias=False, response_model_exclude={'queue'})
async def finish(id_: str, app: App) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.finish(id_)
