from fastapi import APIRouter, HTTPException, status

from minager.core.auth.dependencies import CurrentUserID

from . import dependencies, exceptions, schemas

router = APIRouter(prefix='/learning-sessions')


@router.get(
    '/active',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def get_my_active_session(
    user_id: CurrentUserID,
    learning_sessions: dependencies.LearningSessionServiceDependency,
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
    start_session: dependencies.StartSessionUseCaseDependency,
) -> schemas.LearningSessionSchema:
    try:
        return await start_session.execute(user_id=str(user_id), data=data)
    except exceptions.EmptyQueueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except AssertionError as e:
        # A TraversalOrder member can be declared before a query backs it (e.g. `dfs`);
        # the knowledge tree asserts on those. That is bad input, not a server fault.
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e


@router.post(
    '/{id_}/generate-queue',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def regenerate_queue(
    id_: str,
    regenerate_queue_use_case: dependencies.RegenerateQueueUseCaseDependency,
) -> schemas.LearningSessionSchema:
    try:
        return await regenerate_queue_use_case.execute(id_)
    except exceptions.SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except AssertionError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e)) from e


@router.post(
    '/{id_}/repeat',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def perform_repetition(
    id_: str,
    user_id: CurrentUserID,
    repetition_data: schemas.RecordRepetitionDataSchema,
    perform_repetition_use_case: dependencies.PerformRepetitionUseCaseDependency,
) -> schemas.LearningSessionSchema:
    # TODO: Consider returning only new current node cause only this value actually changes
    try:
        return await perform_repetition_use_case.execute(
            session_id=id_, user_id=str(user_id), **repetition_data.model_dump()
        )
    except exceptions.SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@router.post('/{id_}/finish', response_model_by_alias=False, response_model_exclude={'queue'})
async def finish(
    id_: str,
    learning_sessions: dependencies.LearningSessionServiceDependency,
) -> schemas.LearningSessionSchema:
    try:
        return await learning_sessions.finish(id_)
    except exceptions.SessionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
