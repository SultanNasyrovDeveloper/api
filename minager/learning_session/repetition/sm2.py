from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from minager.node.schemas import NodeDetailSchema

from .base import BaseLearningStrategy


@dataclass
class StudyNodeResult:
    difficulty: float
    interval: float
    next_repetition: datetime


class SuperMemo2LearningStrategy(BaseLearningStrategy):
    def study_node(self, node: NodeDetailSchema, rating: int) -> StudyNodeResult:
        """
        Handle node repetition using supermemo2 strategy.

        https://www.supermemo.com/ru/archives1990-2015/english/ol/sm2
        This is implementation of algorithm described in the link.
        Repetition strategy calculates optimal next repetition datetime of some data item based on
        user repetition rating(subjective repetition quality evaluation).
        """
        interval = 1
        node_difficulty = 2.5 if not node.difficulty else node.difficulty
        result = StudyNodeResult(
            difficulty=node_difficulty,
            interval=interval,
            next_repetition=datetime.now(tz=UTC) + timedelta(days=1),
        )
        if rating >= 3:  # if repetition is positive
            q = rating
            new_difficulty = Decimal(node_difficulty) + Decimal(0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
            result.difficulty = float(new_difficulty.quantize(Decimal('1.0')))

            if node.cpr == 0:
                interval = 1  # if this is first positive repetition repeat this node tomorrow again
            elif node.cpr == 1:
                result.interval = 4  # According to supermemo2 should be 6 days
            else:
                interval = round(node.last_interval * node.difficulty, 1)

        result.next_repetition = datetime.now(UTC) + timedelta(days=float(interval))
        return result
