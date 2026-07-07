from typing import Annotated

from fastapi import Depends

from minager.dependencies import SurrealSession

from .repositories import NodeRepository
from .services import NodeService
from .use_cases import GenerateNodeContentUseCase, MoveNodeUseCase


def get_node_repository(session: SurrealSession) -> NodeRepository:
    return NodeRepository(session=session)


NodeRepositoryDependency = Annotated[NodeRepository, Depends(get_node_repository)]


def get_node_service(repository: NodeRepositoryDependency) -> NodeService:
    return NodeService(repository=repository)


NodeServiceDependency = Annotated[NodeService, Depends(get_node_service)]


def get_move_node_use_case(repository: NodeRepositoryDependency) -> MoveNodeUseCase:
    return MoveNodeUseCase(repository=repository)


MoveNodeUseCaseDependency = Annotated[MoveNodeUseCase, Depends(get_move_node_use_case)]


def get_generate_node_content_use_case(
    repository: NodeRepositoryDependency,
) -> GenerateNodeContentUseCase:
    return GenerateNodeContentUseCase(repository=repository)


GenerateNodeContentUseCaseDependency = Annotated[
    GenerateNodeContentUseCase, Depends(get_generate_node_content_use_case)
]
