from fastapi import APIRouter, Path, status

from minager.dependencies import App, RequestUser

from . import schemas

router = APIRouter(prefix='/learning-sessions')


@router.get(
    '/active',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def get_my_active_session(user: RequestUser, app: App) -> schemas.LearningSessionSchema | None:
    return await app.state.learning_session.get_my_active_session(str(user.sub))


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
        user_id=str(user.sub), data=learning_session.model_dump(mode='json')
    )


@router.post(
    '/{id_}/generate-queue',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def regenerate_queue(
    id_: str = Path(description='Learning session ID'),
    app: App = ...,
) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.regenerate_queue(id_)


@router.post(
    '/{id_}/repeat',
    response_model_by_alias=False,
    response_model_exclude={'queue'},
)
async def perform_repetition(
    id_: str = Path(description='Learning session ID'),
    user: RequestUser = ...,
    repetition_data: schemas.RecordRepetitionDataSchema = ...,
    app: App = ...,
) -> schemas.LearningSessionSchema:
    # TODO: Consider returning only new current node cause only this value actually changes
    return await app.state.learning_session.perform_repetition(
        session_id=id_, user_id=str(user.sub), **repetition_data.model_dump()
    )


@router.post('/{id_}/finish', response_model_by_alias=False, response_model_exclude={'queue'})
async def finish(
    id_: str = Path(description='Learning session ID'),
    app: App = ...,
) -> schemas.LearningSessionSchema:
    return await app.state.learning_session.finish(id_)
