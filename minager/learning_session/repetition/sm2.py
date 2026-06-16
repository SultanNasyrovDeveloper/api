from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol

from .base import BaseLearningStrategy


class ReviewedNode(Protocol):
    difficulty: float
    cpr: int
    last_interval: float | int
    repetitions: int


@dataclass
class StudyNodeResult:
    difficulty: float
    interval: float
    next_repetition: datetime


class SuperMemo2LearningStrategy(BaseLearningStrategy):
    def study_node(self, node: ReviewedNode, rating: int) -> StudyNodeResult:
        """
        Handle node repetition using supermemo2 strategy.

        https://www.supermemo.com/ru/archives1990-2015/english/ol/sm2
        """
        node_difficulty = node.difficulty if node.difficulty else 2.5

        q = rating
        new_difficulty = float(
            (Decimal(str(node_difficulty)) + Decimal(str(0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))).quantize(
                Decimal('1.0')
            )
        )
        difficulty = max(1.3, new_difficulty)

        interval: float = 1
        if rating >= 3:
            if node.cpr == 0:
                interval = 1
            elif node.cpr == 1:
                interval = 4
            else:
                interval = round(node.last_interval * node_difficulty, 1)

        return StudyNodeResult(
            difficulty=difficulty,
            interval=interval,
            next_repetition=datetime.now(UTC) + timedelta(days=float(interval)),
        )
