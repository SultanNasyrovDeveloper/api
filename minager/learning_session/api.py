from typing import Optional

from fastapi import APIRouter, status

from minager.core.api.dependencies import App, RequestUser

from . import schemas

router = APIRouter(prefix='/learning-sessions')


@router.get(
    '/active',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def get_my_active_session(
    user: RequestUser, app: App
) -> Optional[schemas.LearningSessionSchema]:
    return await app.state.learning_session.get_my_active_session(user['id'])


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
        user_id=user['id'], data=learning_session.model_dump(mode='json')
    )


@router.post(
    '/{id_}/generate-queue',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def regenerate_queue(id_: str, app: App) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.regenerate_queue(id_)


@router.post(
    '/{id_}/repeat',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def perform_repetition(
    id_: str,
    user: RequestUser,
    repetition_data: schemas.RecordRepetitionDataSchema,
    app: App,
) -> schemas.LearningSessionSchema:
    # TODO: Consider returning only new current node cause only this value actually changes
    return await app.state.learning_session.perform_repetition(
        session_id=id_, user_id=user['id'], **repetition_data.model_dump()
    )


@router.post('/{id_}/finish', response_model_by_alias=False, response_model_exclude={'queue'})
async def finish(id_: str, app: App) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.finish(id_)
