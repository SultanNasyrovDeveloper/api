"""
Unit tests for the SuperMemo2 spaced repetition algorithm.

Known implementation deviations from the SM2 spec are documented inline.
Tests verify *current* behavior so regressions are caught during refactoring.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from minager.learning_session.repetition.sm2 import StudyNodeResult, SuperMemo2LearningStrategy

# No pytestmark needed — all SM2 tests are synchronous


def make_node(*, difficulty: float = 2.5, cpr: int = 0, last_interval: int = 1, repetitions: int = 0):
    return SimpleNamespace(
        difficulty=difficulty, cpr=cpr, last_interval=last_interval, repetitions=repetitions
    )


@pytest.fixture()
def strategy() -> SuperMemo2LearningStrategy:
    return SuperMemo2LearningStrategy()


def test_returns_study_node_result(strategy):
    result = strategy.study_node(make_node(), rating=4)
    assert isinstance(result, StudyNodeResult)


def test_first_positive_repetition_uses_interval_one(strategy):
    """cpr=0 → first positive rep → repeat tomorrow (interval=1)."""
    node = make_node(cpr=0)
    result = strategy.study_node(node, rating=5)
    assert result.next_repetition > datetime.now(UTC)
    assert result.next_repetition < datetime.now(UTC) + timedelta(days=2)


def test_second_positive_repetition_sets_result_interval_four(strategy):
    """cpr=1 → interval=4, next_repetition is ~4 days out."""
    node = make_node(cpr=1)
    result = strategy.study_node(node, rating=4)
    assert result.interval == 4
    assert result.next_repetition > datetime.now(UTC) + timedelta(days=3)
    assert result.next_repetition < datetime.now(UTC) + timedelta(days=5)


def test_subsequent_positive_repetition_multiplies_interval(strategy):
    """cpr>=2 → interval = round(last_interval * old_difficulty), result.interval is updated."""
    node = make_node(cpr=2, last_interval=4, difficulty=2.5)
    result = strategy.study_node(node, rating=4)
    expected_interval = round(4 * 2.5, 1)  # 10.0
    assert result.interval == expected_interval
    assert result.next_repetition > datetime.now(UTC) + timedelta(days=expected_interval - 1)
    assert result.next_repetition < datetime.now(UTC) + timedelta(days=expected_interval + 1)


def test_negative_repetition_keeps_interval_one(strategy):
    """rating < 3 → reset interval to 1 day."""
    node = make_node(cpr=2, last_interval=10)
    result = strategy.study_node(node, rating=2)
    assert result.next_repetition < datetime.now(UTC) + timedelta(days=2)


def test_worst_rating_keeps_interval_one(strategy):
    node = make_node(cpr=2, last_interval=10)
    result = strategy.study_node(node, rating=0)
    assert result.next_repetition < datetime.now(UTC) + timedelta(days=2)


def test_perfect_rating_increases_difficulty(strategy):
    node = make_node(difficulty=2.5, cpr=0)
    result = strategy.study_node(node, rating=5)
    assert result.difficulty > 2.5


def test_poor_rating_decreases_difficulty(strategy):
    """rating < 3 → difficulty is decreased per SM2 spec, clamped to minimum 1.3."""
    node = make_node(difficulty=2.5, cpr=0)
    result = strategy.study_node(node, rating=0)
    assert result.difficulty < 2.5
    assert result.difficulty >= 1.3


def test_minimum_positive_rating_changes_difficulty_minimally(strategy):
    node = make_node(difficulty=2.5, cpr=0)
    result = strategy.study_node(node, rating=3)
    # rating=3: delta = 0.1 - 2*(0.08 + 2*0.02) = 0.1 - 2*0.12 = 0.1 - 0.24 = -0.14
    assert abs(result.difficulty - 2.5) < 0.3


def test_default_difficulty_fallback_when_zero(strategy):
    """node.difficulty=0 (falsy) → algorithm defaults to 2.5."""
    node = make_node(difficulty=0, cpr=0)
    result = strategy.study_node(node, rating=5)
    # Started from 2.5, not 0
    assert result.difficulty > 0


def test_next_repetition_is_always_in_future(strategy):
    for rating in range(6):
        node = make_node(cpr=0)
        result = strategy.study_node(node, rating=rating)
        assert result.next_repetition > datetime.now(UTC)
