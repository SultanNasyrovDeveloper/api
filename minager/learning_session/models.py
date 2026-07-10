from datetime import UTC, datetime, timedelta

from pydantic import Field, computed_field

from minager.core.clients.knowledge_tree import SubtreeFilter, TraversalOrder
from minager.core.db.mongodb import MongoDBModel

from . import enums


class LearningSession(MongoDBModel):
    """
    MongoDB model for learning sessions.

    Represents an active or completed learning session where a user reviews
    nodes from a target subtree using spaced repetition.
    """

    is_active: bool = Field(default=True, description='Whether session is currently active')
    user_id: str = Field(description='ID of the user who owns this session')
    targets: list[str] = Field(description='Root node IDs of the subtrees being studied')

    # Node queues
    current_node: str | None = Field(default=None, description='Node ID currently being reviewed')
    queue: list[str] = Field(default_factory=list, description='Main review queue of node IDs')
    bad_repetition_queue: list[str] = Field(
        default_factory=list,
        description='Queue of node IDs that received poor ratings (< 3) and need re-review',
    )

    # Timestamps
    start_datetime: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description='When the session was started',
    )
    last_activity_datetime: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC),
        description='Last time the session was interacted with',
    )
    finish_datetime: datetime | None = Field(
        default=None, description='When the session was finished (if completed)'
    )

    # Strategies
    filter_strategy: SubtreeFilter = Field(
        default=SubtreeFilter.all,
        description='Which nodes of the target subtrees belong in the queue',
    )
    traversal_order: TraversalOrder = Field(
        default=TraversalOrder.random,
        description='Order in which the target subtrees are walked to build the queue',
    )
    repetition_strategy: enums.RepetitionStrategy = Field(
        default=enums.RepetitionStrategy.sm2,
        description='Spaced repetition algorithm to use (e.g., SuperMemo2)',
    )

    @computed_field
    @property
    def is_expired(self) -> bool:
        """Check if session has been inactive for more than 1 hour."""
        # TODO: Extract expiration time to application config
        return self.last_activity_datetime.replace(tzinfo=UTC) < datetime.now(tz=UTC) - timedelta(hours=1)

    @computed_field
    @property
    def total_nodes_remaining(self) -> int:
        """Total number of nodes remaining in both queues."""
        return len(self.queue) + len(self.bad_repetition_queue)

    @computed_field
    @property
    def has_nodes_remaining(self) -> bool:
        """Check if there are any nodes left to review."""
        return self.current_node is not None or bool(self.queue) or bool(self.bad_repetition_queue)
