from app.graph.knowledge_graph_builder import (
    CallEdgeInput,
    ClassInput,
    DirectoryInput,
    FileInput,
    FunctionInput,
    ImportEdgeInput,
    MethodInput,
    build_graph,
)


def _node_keys(result):
    return {(n.node_type, n.ref_id) for n in result.nodes}


def _edges(result):
    return {(e.source_key, e.target_key, e.edge_type) for e in result.edges}


def test_builds_repository_folder_file_containment_chain():
    result = build_graph(
        repository_id="repo-1",
        directories=[DirectoryInput(id="dir-src", name="src", parent_id=None)],
        files=[FileInput(id="file-1", filename="main.py", directory_id="dir-src", language="python")],
        classes=[],
        methods=[],
        functions=[],
        calls=[],
        imports=[],
    )
    assert ("repository", "repo-1") in _node_keys(result)
    assert ("folder", "dir-src") in _node_keys(result)
    assert ("file", "file-1") in _node_keys(result)
    assert (("repository", "repo-1"), ("folder", "dir-src"), "contains") in _edges(result)
    assert (("folder", "dir-src"), ("file", "file-1"), "contains") in _edges(result)


def test_nested_directories_get_correct_parent_edges_regardless_of_input_order():
    # Deliberately out of depth order -- the pure sort-by-depth in the builder
    # should handle this correctly either way.
    result = build_graph(
        repository_id="repo-1",
        directories=[
            DirectoryInput(id="dir-deep", name="services", parent_id="dir-mid"),
            DirectoryInput(id="dir-top", name="app", parent_id=None),
            DirectoryInput(id="dir-mid", name="app", parent_id="dir-top"),
        ],
        files=[],
        classes=[],
        methods=[],
        functions=[],
        calls=[],
        imports=[],
    )
    edges = _edges(result)
    assert (("repository", "repo-1"), ("folder", "dir-top"), "contains") in edges
    assert (("folder", "dir-top"), ("folder", "dir-mid"), "contains") in edges
    assert (("folder", "dir-mid"), ("folder", "dir-deep"), "contains") in edges


def test_file_directly_in_repository_root_has_no_directory_id():
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-1", filename="README.md", directory_id=None, language=None)],
        classes=[],
        methods=[],
        functions=[],
        calls=[],
        imports=[],
    )
    assert (("repository", "repo-1"), ("file", "file-1"), "contains") in _edges(result)


def test_class_inheritance_produces_inherits_edge():
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-1", filename="models.py", directory_id=None, language="python")],
        classes=[
            ClassInput(id="cls-base", file_id="file-1", name="Repository", parent_class_id=None),
            ClassInput(id="cls-sub", file_id="file-1", name="UserRepository", parent_class_id="cls-base"),
        ],
        methods=[],
        functions=[],
        calls=[],
        imports=[],
    )
    edges = _edges(result)
    assert (("class", "cls-sub"), ("class", "cls-base"), "inherits") in edges
    assert (("file", "file-1"), ("class", "cls-base"), "contains") in edges
    assert (("file", "file-1"), ("class", "cls-sub"), "contains") in edges


def test_inheritance_from_a_class_outside_this_repository_is_dropped_not_crashed():
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-1", filename="models.py", directory_id=None, language="python")],
        classes=[ClassInput(id="cls-sub", file_id="file-1", name="MyModel", parent_class_id="some-external-id")],
        methods=[],
        functions=[],
        calls=[],
        imports=[],
    )
    assert not any(e.edge_type == "inherits" for e in result.edges)


def test_method_nests_under_its_class_and_function_under_its_file():
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-1", filename="app.py", directory_id=None, language="python")],
        classes=[ClassInput(id="cls-1", file_id="file-1", name="Service", parent_class_id=None)],
        methods=[MethodInput(id="m-1", class_id="cls-1", name="run")],
        functions=[FunctionInput(id="fn-1", file_id="file-1", name="helper")],
        calls=[],
        imports=[],
    )
    edges = _edges(result)
    assert (("class", "cls-1"), ("method", "m-1"), "contains") in edges
    assert (("file", "file-1"), ("function", "fn-1"), "contains") in edges


def test_resolved_calls_produce_deduped_weighted_edges():
    calls = [
        CallEdgeInput(caller_function_id="fn-a", caller_method_id=None, callee_function_id="fn-b", callee_method_id=None),
        CallEdgeInput(caller_function_id="fn-a", caller_method_id=None, callee_function_id="fn-b", callee_method_id=None),
        CallEdgeInput(caller_function_id="fn-a", caller_method_id=None, callee_function_id="fn-b", callee_method_id=None),
    ]
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-1", filename="app.py", directory_id=None, language="python")],
        classes=[],
        methods=[],
        functions=[
            FunctionInput(id="fn-a", file_id="file-1", name="a"),
            FunctionInput(id="fn-b", file_id="file-1", name="b"),
        ],
        calls=calls,
        imports=[],
    )
    call_edges = [e for e in result.edges if e.edge_type == "calls"]
    assert len(call_edges) == 1, "three calls between the same pair should dedupe to one weighted edge"
    assert call_edges[0].weight == 3.0
    assert call_edges[0].source_key == ("function", "fn-a")
    assert call_edges[0].target_key == ("function", "fn-b")


def test_unresolved_call_produces_no_edge():
    calls = [CallEdgeInput(caller_function_id="fn-a", caller_method_id=None, callee_function_id=None, callee_method_id=None)]
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-1", filename="app.py", directory_id=None, language="python")],
        classes=[],
        methods=[],
        functions=[FunctionInput(id="fn-a", file_id="file-1", name="a")],
        calls=calls,
        imports=[],
    )
    assert not any(e.edge_type == "calls" for e in result.edges)


def test_resolved_import_produces_edge_between_files():
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[
            FileInput(id="file-a", filename="a.py", directory_id=None, language="python"),
            FileInput(id="file-b", filename="b.py", directory_id=None, language="python"),
        ],
        classes=[],
        methods=[],
        functions=[],
        calls=[],
        imports=[ImportEdgeInput(file_id="file-a", resolved_file_id="file-b")],
    )
    assert (("file", "file-a"), ("file", "file-b"), "imports") in _edges(result)


def test_unresolved_import_produces_no_edge():
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-a", filename="a.py", directory_id=None, language="python")],
        classes=[],
        methods=[],
        functions=[],
        calls=[],
        imports=[ImportEdgeInput(file_id="file-a", resolved_file_id=None)],
    )
    assert not any(e.edge_type == "imports" for e in result.edges)


def test_self_import_produces_no_edge():
    # Shouldn't normally happen, but a self-loop "imports" edge would be noise, not
    # information.
    result = build_graph(
        repository_id="repo-1",
        directories=[],
        files=[FileInput(id="file-a", filename="a.py", directory_id=None, language="python")],
        classes=[],
        methods=[],
        functions=[],
        calls=[],
        imports=[ImportEdgeInput(file_id="file-a", resolved_file_id="file-a")],
    )
    assert not any(e.edge_type == "imports" for e in result.edges)
