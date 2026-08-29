from app.analysis.circular_dependency_detector import find_circular_dependencies
from app.analysis.dependency_graph import build_adjacency, resolve_imports


def test_resolves_internal_import_to_a_file_id():
    edges = resolve_imports(
        imports_by_file={"file-a": ["file_b_module"]},
        file_ids_by_module_path={"file_b_module": "file-b"},
    )
    assert len(edges) == 1
    assert edges[0].imported_file_id == "file-b"
    assert edges[0].is_external is False


def test_unresolvable_import_is_treated_as_external():
    edges = resolve_imports(
        imports_by_file={"file-a": ["requests"]},
        file_ids_by_module_path={},
    )
    assert len(edges) == 1
    assert edges[0].imported_file_id is None
    assert edges[0].is_external is True


def test_build_adjacency_drops_external_edges():
    edges = resolve_imports(
        imports_by_file={"file-a": ["file_b_module", "requests"]},
        file_ids_by_module_path={"file_b_module": "file-b"},
    )
    adjacency = build_adjacency(edges)
    assert adjacency == {"file-a": {"file-b"}}


def test_end_to_end_with_circular_dependency_detector():
    # Two files import each other -- resolve_imports/build_adjacency feeding
    # straight into the (separately, exhaustively tested) cycle detector, as a
    # slice of what actually happens once Phase 6 wires this into real file data.
    imports_by_file = {"file-a": ["file_b_module"], "file-b": ["file_a_module"]}
    file_ids_by_module = {"file_b_module": "file-b", "file_a_module": "file-a"}

    edges = resolve_imports(imports_by_file, file_ids_by_module)
    adjacency = build_adjacency(edges)
    cycles = find_circular_dependencies(adjacency)

    assert len(cycles) == 1
    assert set(cycles[0]) == {"file-a", "file-b"}
