"""Pure, DB-agnostic projection from parsed entities (files, directories, classes,
methods, functions, resolved calls, resolved imports) into the generic
knowledge_nodes/knowledge_edges graph. Takes plain dataclasses, returns a plan of
what to write -- no ORM rows, no session -- which is what makes it testable without
a database, the same pattern as app/analysis/dependency_graph.py and
call_graph_resolver.py. app/services/knowledge_graph_service.py is the thin sync
wrapper that fetches real rows, calls this, and persists what it returns.

Node keys are (node_type, ref_id) pairs throughout, matching the polymorphic
(node_type, ref_id) shape of the knowledge_nodes table itself.
"""

from dataclasses import dataclass, field

NodeKey = tuple[str, str]


@dataclass(frozen=True)
class DirectoryInput:
    id: str
    name: str
    parent_id: str | None


@dataclass(frozen=True)
class FileInput:
    id: str
    filename: str
    directory_id: str | None
    language: str | None


@dataclass(frozen=True)
class ClassInput:
    id: str
    file_id: str
    name: str
    parent_class_id: str | None


@dataclass(frozen=True)
class MethodInput:
    id: str
    class_id: str
    name: str


@dataclass(frozen=True)
class FunctionInput:
    id: str
    file_id: str
    name: str


@dataclass(frozen=True)
class CallEdgeInput:
    caller_function_id: str | None
    caller_method_id: str | None
    callee_function_id: str | None
    callee_method_id: str | None


@dataclass(frozen=True)
class ImportEdgeInput:
    file_id: str
    resolved_file_id: str | None


@dataclass(frozen=True)
class GraphNodeInput:
    node_type: str
    ref_id: str
    label: str
    metadata: dict = field(default_factory=dict)
    parent_key: NodeKey | None = None  # None only for the repository root itself


@dataclass(frozen=True)
class GraphEdgeInput:
    source_key: NodeKey
    target_key: NodeKey
    edge_type: str
    weight: float = 1.0


@dataclass
class GraphBuildResult:
    nodes: list[GraphNodeInput] = field(default_factory=list)
    edges: list[GraphEdgeInput] = field(default_factory=list)


def build_graph(
    repository_id: str,
    directories: list[DirectoryInput],
    files: list[FileInput],
    classes: list[ClassInput],
    methods: list[MethodInput],
    functions: list[FunctionInput],
    calls: list[CallEdgeInput],
    imports: list[ImportEdgeInput],
) -> GraphBuildResult:
    result = GraphBuildResult()
    repo_key: NodeKey = ("repository", repository_id)
    result.nodes.append(GraphNodeInput(node_type="repository", ref_id=repository_id, label="repository"))

    dir_by_id = {d.id: d for d in directories}
    for d in sorted(directories, key=lambda d: _directory_depth(d, dir_by_id)):
        parent_key = ("folder", d.parent_id) if d.parent_id else repo_key
        result.nodes.append(
            GraphNodeInput(node_type="folder", ref_id=d.id, label=d.name, parent_key=parent_key)
        )

    for f in files:
        parent_key = ("folder", f.directory_id) if f.directory_id else repo_key
        result.nodes.append(
            GraphNodeInput(
                node_type="file",
                ref_id=f.id,
                label=f.filename,
                metadata={"language": f.language} if f.language else {},
                parent_key=parent_key,
            )
        )

    for c in classes:
        result.nodes.append(
            GraphNodeInput(node_type="class", ref_id=c.id, label=c.name, parent_key=("file", c.file_id))
        )

    for m in methods:
        result.nodes.append(
            GraphNodeInput(node_type="method", ref_id=m.id, label=m.name, parent_key=("class", m.class_id))
        )

    for fn in functions:
        result.nodes.append(
            GraphNodeInput(node_type="function", ref_id=fn.id, label=fn.name, parent_key=("file", fn.file_id))
        )

    node_keys = {(n.node_type, n.ref_id) for n in result.nodes}
    valid_parent_keys = node_keys | {repo_key}

    # "contains" edges: one per node with a parent that actually exists in this
    # graph. A missing parent (a class whose file somehow isn't in `files`) just
    # means no edge for that node rather than a crash -- the node itself is still
    # created and reachable directly.
    for node in result.nodes:
        if node.parent_key is not None and node.parent_key in valid_parent_keys:
            result.edges.append(
                GraphEdgeInput(source_key=node.parent_key, target_key=(node.node_type, node.ref_id), edge_type="contains")
            )

    for c in classes:
        if c.parent_class_id and ("class", c.parent_class_id) in node_keys:
            result.edges.append(
                GraphEdgeInput(source_key=("class", c.id), target_key=("class", c.parent_class_id), edge_type="inherits")
            )

    # "calls" edges are deduped and weighted by call-site count rather than one row
    # per call site -- more useful for a call-graph view (Phase 9) than N parallel
    # edges between the same two nodes.
    call_counts: dict[tuple[NodeKey, NodeKey], int] = {}
    for call in calls:
        caller_key = ("function", call.caller_function_id) if call.caller_function_id else ("method", call.caller_method_id)
        if call.callee_function_id:
            callee_key: NodeKey = ("function", call.callee_function_id)
        elif call.callee_method_id:
            callee_key = ("method", call.callee_method_id)
        else:
            continue  # unresolved call -- nothing to draw an edge to
        if caller_key in node_keys and callee_key in node_keys:
            call_counts[(caller_key, callee_key)] = call_counts.get((caller_key, callee_key), 0) + 1
    for (caller_key, callee_key), count in call_counts.items():
        result.edges.append(GraphEdgeInput(source_key=caller_key, target_key=callee_key, edge_type="calls", weight=float(count)))

    for imp in imports:
        if imp.resolved_file_id is None:
            continue
        source_key: NodeKey = ("file", imp.file_id)
        target_key: NodeKey = ("file", imp.resolved_file_id)
        if source_key in node_keys and target_key in node_keys and source_key != target_key:
            result.edges.append(GraphEdgeInput(source_key=source_key, target_key=target_key, edge_type="imports"))

    return result


def _directory_depth(directory: DirectoryInput, dir_by_id: dict[str, DirectoryInput]) -> int:
    depth = 0
    current = directory
    seen = {directory.id}
    while current.parent_id and current.parent_id in dir_by_id:
        if current.parent_id in seen:
            break  # malformed/cyclic parent chain -- stop rather than loop forever
        current = dir_by_id[current.parent_id]
        seen.add(current.id)
        depth += 1
    return depth
