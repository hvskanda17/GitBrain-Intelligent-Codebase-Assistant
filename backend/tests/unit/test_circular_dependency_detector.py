from app.analysis.circular_dependency_detector import find_circular_dependencies


def test_finds_a_three_node_cycle():
    adjacency = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
    cycles = find_circular_dependencies(adjacency)
    assert len(cycles) == 1
    assert set(cycles[0]) == {"A", "B", "C"}


def test_linear_chain_has_no_cycle():
    adjacency = {"A": {"B"}, "B": {"C"}}
    assert find_circular_dependencies(adjacency) == []


def test_self_loop_is_a_cycle():
    adjacency = {"A": {"A"}}
    cycles = find_circular_dependencies(adjacency)
    assert cycles == [["A"]]


def test_finds_multiple_disjoint_cycles():
    adjacency = {"A": {"B"}, "B": {"A"}, "C": {"D"}, "D": {"C"}, "E": {"A"}}
    cycles = find_circular_dependencies(adjacency)
    cycle_sets = [set(c) for c in cycles]
    assert {"A", "B"} in cycle_sets
    assert {"C", "D"} in cycle_sets
    assert len(cycles) == 2


def test_deep_chain_does_not_blow_the_recursion_limit():
    # The whole point of the iterative (not recursive) implementation.
    adjacency = {str(i): {str(i + 1)} for i in range(2000)}
    assert find_circular_dependencies(adjacency) == []
