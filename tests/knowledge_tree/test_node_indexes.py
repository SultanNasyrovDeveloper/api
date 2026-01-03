from datetime import datetime
from types import SimpleNamespace

import pytest

from minager.node.node_indexes import NodeIndex, NodeOverallIndex, NodeSubtreeIndex


def make_node(
    repetitions=0,
    cpr=0,
    last_rating=0,
    difficulty=0.5,
    days_since_last_rep=None,
):
    node = SimpleNamespace()
    node.repetitions = repetitions
    node.cpr = cpr
    node.last_rating = last_rating
    node.difficulty = difficulty

    if days_since_last_rep is not None:
        node.days_since_last_rep = days_since_last_rep
        node.last_repetition = datetime.now()
    else:
        node.days_since_last_rep = None
        node.last_repetition = None

    return node


def make_stats(
    size=0,
    count=0,
    average_rating=0,
    empty_nodes=0,
    outdated=0,
    not_visited=0,
):
    return SimpleNamespace(
        size=size,
        count=count,
        average_rating=average_rating,
        empty_nodes=empty_nodes,
        outdated=outdated,
        not_visited=not_visited,
    )


def test_node_index_is_between_0_and_1():
    node = make_node(
        repetitions=5,
        cpr=3,
        last_rating=4,
        difficulty=0.5,
        days_since_last_rep=2,
    )

    result = NodeIndex(node).calculate()

    assert 0 <= result['index'] <= 1


def test_node_with_no_activity_should_be_near_zero():
    node = make_node(
        repetitions=0,
        cpr=0,
        last_rating=0,
        days_since_last_rep=None,
    )

    result = NodeIndex(node).calculate()

    assert result['index'] == 0 or result['index'] < 0.1


def test_more_repetitions_increase_index():
    low = NodeIndex(make_node(repetitions=1, last_rating=3)).calculate()['index']
    high = NodeIndex(make_node(repetitions=10, last_rating=3)).calculate()['index']

    assert high > low


def test_bad_rating_penalizes_index():
    good = NodeIndex(make_node(repetitions=5, last_rating=5)).calculate()['index']
    bad = NodeIndex(make_node(repetitions=5, last_rating=1)).calculate()['index']

    assert bad < good


def test_subtree_index_is_zero_if_size_zero():
    stats = make_stats(size=0)

    result = NodeSubtreeIndex(stats).calculate()

    assert result['index'] == 0
    assert result['empty'] is True


def test_subtree_with_good_structure_scores_higher():
    weak = NodeSubtreeIndex(
        make_stats(
            size=10,
            count=2,
            average_rating=2,
            empty_nodes=5,
            not_visited=6,
        )
    ).calculate()['index']

    strong = NodeSubtreeIndex(
        make_stats(
            size=10,
            count=10,
            average_rating=4.5,
            empty_nodes=0,
            not_visited=0,
        )
    ).calculate()['index']

    assert strong > weak


def test_empty_nodes_penalize_index():
    low_penalty = NodeSubtreeIndex(make_stats(size=10, empty_nodes=1)).calculate()['index']
    high_penalty = NodeSubtreeIndex(make_stats(size=10, empty_nodes=8)).calculate()['index']

    assert high_penalty < low_penalty


def test_overall_uses_node_only_when_no_subtree():
    node = make_node(repetitions=5, last_rating=4)
    stats = make_stats(size=0)

    overall = NodeOverallIndex(node, stats).calculate()
    node_index = NodeIndex(node).calculate()['index']

    assert overall['subtree_index'] == 0
    assert overall['overall_index'] == pytest.approx(node_index)


def test_overall_penalized_by_bad_subtree():
    node = make_node(repetitions=10, last_rating=5)

    strong_tree = make_stats(
        size=10,
        count=10,
        average_rating=5,
        empty_nodes=0,
        not_visited=0,
    )

    weak_tree = make_stats(
        size=10,
        count=2,
        average_rating=2,
        empty_nodes=6,
        not_visited=6,
    )

    strong = NodeOverallIndex(node, strong_tree).calculate()['overall_index']
    weak = NodeOverallIndex(node, weak_tree).calculate()['overall_index']

    assert weak < strong


def test_subtree_weight_increases_with_size():
    node = make_node(repetitions=5, last_rating=4)

    small = NodeOverallIndex(node, make_stats(size=1, count=1)).calculate()['weights']['subtree']
    large = NodeOverallIndex(node, make_stats(size=50, count=50)).calculate()['weights']['subtree']

    assert large > small
