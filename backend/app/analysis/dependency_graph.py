"""Builds a file-level dependency graph from ImportEntity data. Language-agnostic:
every parser's extract_imports() produces the same (source_module, imported_symbol)
shape regardless of whether the underlying syntax was `import x`, `from x import y`,
or `require('x')`."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ImportEdge:
    importing_file_id: str
    imported_file_id: str | None  # None when the import resolves outside the repo
    source_module: str
    is_external: bool


def resolve_imports(
    imports_by_file: dict[str, list[str]],
    file_ids_by_module_path: dict[str, str],
) -> list[ImportEdge]:
    """`imports_by_file` maps a file's id to the list of module paths it imports.
    `file_ids_by_module_path` maps a resolvable internal module path (however the
    caller chooses to normalize it -- e.g. 'app.services.auth_service' or
    'src/lib/api') to that file's id. Anything not found there is treated as an
    external package import."""
    edges: list[ImportEdge] = []
    for file_id, modules in imports_by_file.items():
        for module in modules:
            target_id = file_ids_by_module_path.get(module)
            edges.append(
                ImportEdge(
                    importing_file_id=file_id,
                    imported_file_id=target_id,
                    source_module=module,
                    is_external=target_id is None,
                )
            )
    return edges


def build_adjacency(edges: list[ImportEdge]) -> dict[str, set[str]]:
    """Internal-only adjacency (importing_file_id -> set of imported_file_id),
    dropping external packages -- the shape circular_dependency_detector.py and any
    later graph traversal actually want."""
    adjacency: dict[str, set[str]] = {}
    for edge in edges:
        if edge.imported_file_id is None:
            continue
        adjacency.setdefault(edge.importing_file_id, set()).add(edge.imported_file_id)
    return adjacency
