from datetime import UTC, datetime

from surorm.data_model import Datetime

from minager.core.clients.knowledge_tree import KnowledgeTreeClient

from . import exceptions
from .models import LearningSession
from .repetition.sm2 import SuperMemo2LearningStrategy
from .repositories import LearningSessionRepository
from .services import LearningSessionService
from .utils import shuffle

DEFAULT_QUEUE_LIMIT = 50


async def _build_shuffled_queue(
    knowledge_tree_client: KnowledgeTreeClient, targets: list[str], limit: int = DEFAULT_QUEUE_LIMIT
) -> list[str]:
    repetition_queue = await knowledge_tree_client.get_subtree_ids(targets, limit=limit)
    return shuffle(repetition_queue)


class StartSessionUseCase:
    """Returns the caller's existing active session, replacing it if expired, or starts a new one."""

    def __init__(
        self,
        repository: LearningSessionRepository,
        service: LearningSessionService,
        knowledge_tree_client: KnowledgeTreeClient,
    ):
        self.repository = repository
        self.service = service
        self.knowledge_tree_client = knowledge_tree_client

    async def execute(self, user_id: str, data: dict) -> LearningSession:
        already_active = await self.repository.find_active_for_user(user_id)
        if already_active:
            if not already_active.is_expired:
                return already_active
            assert already_active.id
            await self.service.finish(str(already_active.id))

        targets = data.get('targets')
        shuffled_queue = await _build_shuffled_queue(self.knowledge_tree_client, targets)
        session = LearningSession(
            user_id=user_id,
            targets=targets,
            current_node=shuffled_queue[0] if shuffled_queue else None,
            queue=shuffled_queue[1:] if len(shuffled_queue) > 1 else [],
        )
        return await self.repository.save(session)


class RegenerateQueueUseCase:
    def __init__(self, repository: LearningSessionRepository, knowledge_tree_client: KnowledgeTreeClient):
        self.repository = repository
        self.knowledge_tree_client = knowledge_tree_client

    async def execute(self, id_: str) -> LearningSession:
        session = await self.repository.get(id_)
        if not session:
            raise exceptions.SessionNotFoundError
        shuffled_queue = await _build_shuffled_queue(self.knowledge_tree_client, session.targets)
        update_data = {
            'current_node': shuffled_queue[0] if shuffled_queue else None,
            'queue': shuffled_queue[1:] if len(shuffled_queue) > 1 else [],
        }
        return await self.repository.update(id_, update_data)


class PerformRepetitionUseCase:
    def __init__(self, repository: LearningSessionRepository, knowledge_tree_client: KnowledgeTreeClient):
        self.repository = repository
        self.knowledge_tree_client = knowledge_tree_client
        self.learning_strategy = SuperMemo2LearningStrategy()

    async def execute(self, session_id: str, node_id: str, rating: int, user_id: str) -> LearningSession:
        session = await self.repository.get(session_id)
        if not session or session.user_id != user_id:
            raise exceptions.SessionNotFoundError

        repeated_node = await self.knowledge_tree_client.get(node_id)
        study_result = self.learning_strategy.study_node(repeated_node, rating)
        await self.knowledge_tree_client.update(
            repeated_node,
            **{
                # TODO: Datetime usage is just a temp fix. Add proper values handling in surorm
                'last_repetition': Datetime(datetime.now(UTC)),
                'difficulty': study_result.difficulty,
                'last_interval': study_result.interval,
                'next_optimal_repetition': Datetime(study_result.next_repetition),
                'repetitions': repeated_node.repetitions + 1,
                'cpr': repeated_node.cpr + 1 if rating >= 3 else 0,
            },
        )

        session_update_data: dict = {'last_activity_datetime': datetime.now(UTC)}
        session.queue = [n for n in session.queue if n != node_id]
        if node_id == session.current_node:
            if not session.queue and session.bad_repetition_queue:
                session_update_data['current_node'] = session.bad_repetition_queue[0]
                session_update_data['queue'] = (
                    session.bad_repetition_queue[1:] if len(session.bad_repetition_queue) > 1 else []
                )
                session_update_data['bad_repetition_queue'] = []
            else:
                session_update_data['current_node'] = session.queue[0] if session.queue else None
                session_update_data['queue'] = session.queue[1:] if len(session.queue) > 1 else []
        if rating < 3:
            session_update_data['bad_repetition_queue'] = [*session.bad_repetition_queue, node_id]

        return await self.repository.update(session.id, session_update_data)
