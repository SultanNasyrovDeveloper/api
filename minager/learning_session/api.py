from fastapi import APIRouter, status

from minager.core.auth.dependencies import CurrentUserID

from . import dependencies, schemas

router = APIRouter(prefix='/learning-sessions')


@router.get(
    '/active',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def get_my_active_session(
    user_id: CurrentUserID,
    learning_sessions: dependencies.LearningSessionManagerDependency,
) -> schemas.LearningSessionSchema | None:
    return await learning_sessions.get_my_active_session(str(user_id))


@router.post(
    '/start',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
    status_code=status.HTTP_201_CREATED,
)
async def start(
    user_id: CurrentUserID,
    data: schemas.StartLearningSessionSchema,
    learning_sessions: dependencies.LearningSessionManagerDependency,
) -> schemas.LearningSessionSchema:
    return await learning_sessions.start(user_id=str(user_id), data=data.model_dump(mode='json'))


@router.post(
    '/{id_}/generate-queue',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def regenerate_queue(
    id_: str,
    learning_sessions: dependencies.LearningSessionManagerDependency,
) -> schemas.LearningSessionSchema:
    return await learning_sessions.regenerate_queue(id_)


@router.post(
    '/{id_}/repeat',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def perform_repetition(
    id_: str,
    user_id: CurrentUserID,
    repetition_data: schemas.RecordRepetitionDataSchema,
    learning_sessions: dependencies.LearningSessionManagerDependency,
) -> schemas.LearningSessionSchema:
    # TODO: Consider returning only new current node cause only this value actually changes
    return await learning_sessions.perform_repetition(
        session_id=id_, user_id=str(user_id), **repetition_data.model_dump()
    )


@router.post('/{id_}/finish', response_model_by_alias=False, response_model_exclude={'queue'})
async def finish(
    id_: str,
    learning_sessions: dependencies.LearningSessionManagerDependency,
) -> schemas.LearningSessionSchema:
    return await learning_sessions.finish(id_)
