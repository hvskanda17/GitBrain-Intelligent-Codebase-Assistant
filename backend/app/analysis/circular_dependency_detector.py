"""Finds circular import chains in a file dependency graph using Tarjan's strongly-
connected-components algorithm. Any SCC with more than one node is a cycle (a single
node is only a cycle if it imports itself, handled as a special case). Iterative, not
recursive -- a real repository's import graph can be deep enough to blow Python's
default recursion limit with a naive recursive implementation."""


def find_circular_dependencies(adjacency: dict[str, set[str]]) -> list[list[str]]:
    """Returns every cycle as a list of node ids in the cycle (order is the
    traversal order, not necessarily the shortest path around the cycle)."""
    index_counter = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    sccs: list[list[str]] = []

    all_nodes = set(adjacency.keys()) | {n for neighbors in adjacency.values() for n in neighbors}

    for start_node in all_nodes:
        if start_node in indices:
            continue

        # Explicit work-stack DFS (iterative Tarjan) -- each frame is
        # (node, iterator-position-in-its-neighbor-list).
        work: list[tuple[str, list[str], int]] = [(start_node, sorted(adjacency.get(start_node, set())), 0)]
        indices[start_node] = index_counter
        lowlinks[start_node] = index_counter
        index_counter += 1
        stack.append(start_node)
        on_stack.add(start_node)

        while work:
            node, neighbors, i = work[-1]

            if i < len(neighbors):
                work[-1] = (node, neighbors, i + 1)
                neighbor = neighbors[i]
                if neighbor not in indices:
                    indices[neighbor] = index_counter
                    lowlinks[neighbor] = index_counter
                    index_counter += 1
                    stack.append(neighbor)
                    on_stack.add(neighbor)
                    work.append((neighbor, sorted(adjacency.get(neighbor, set())), 0))
                elif neighbor in on_stack:
                    lowlinks[node] = min(lowlinks[node], indices[neighbor])
            else:
                work.pop()
                if work:
                    parent = work[-1][0]
                    lowlinks[parent] = min(lowlinks[parent], lowlinks[node])

                if lowlinks[node] == indices[node]:
                    scc: list[str] = []
                    while True:
                        member = stack.pop()
                        on_stack.discard(member)
                        scc.append(member)
                        if member == node:
                            break
                    if len(scc) > 1 or node in adjacency.get(node, set()):
                        sccs.append(scc)

    return sccs
