"""Resolves import statements to actual files within the repository, for the one
language this project's parser currently covers (Python -- see
app/parsers/registry.py). Absolute dotted-path imports only
(`from app.services.auth_service import AuthService`); relative imports (`from .
import foo`, `from ..sibling import bar`) are a known, documented gap -- Phase 5's
parser was never executed against a real tree-sitter parser (see backend/README.md),
so it isn't yet confirmed whether it even extracts the relative-import node shape
correctly, and resolving something whose extraction is itself unverified isn't
worth the complexity yet. Every other language in
app.parsers.tree_sitter_manager.LANGUAGE_PACK_NAMES has no parser at all, so this
resolver only ever sees Python source_module strings in practice.
"""

from dataclasses import dataclass

PACKAGE_INIT_FILENAME = "__init__.py"


@dataclass(frozen=True)
class ResolvableFile:
    id: str
    path: str  # repository-relative, e.g. "app/services/auth_service.py"
    language: str | None


def compute_module_path(file_path: str) -> str | None:
    """'app/services/auth_service.py' -> 'app.services.auth_service'.
    '__init__.py' maps to its containing package: 'app/services/__init__.py' ->
    'app.services'. Anything not ending in .py returns None (not a Python module)."""
    if not file_path.endswith(".py"):
        return None

    parts = file_path.split("/")
    filename = parts[-1]
    directories = parts[:-1]
    stem = filename[: -len(".py")]

    if filename == PACKAGE_INIT_FILENAME:
        module_parts = directories
    else:
        module_parts = [*directories, stem]

    # A root-level __init__.py has an empty module_parts list -- deliberately
    # returning None here rather than "" (an empty-string module path nothing
    # would ever actually import) rather than a bug: an empty list is falsy, so
    # this reads as "no resolvable module path" by construction, not by accident.
    return ".".join(module_parts) if module_parts else None


def build_module_path_index(files: list[ResolvableFile]) -> dict[str, str]:
    """module dotted-path -> file id, for every Python file in the repository."""
    index: dict[str, str] = {}
    for f in files:
        if f.language != "python":
            continue
        module_path = compute_module_path(f.path)
        if module_path:
            index[module_path] = f.id
    return index


def resolve_import(source_module: str, imported_symbol: str, module_index: dict[str, str]) -> str | None:
    """Returns the file id `source_module` resolves to within this repository, or
    None if it doesn't (almost certainly an external package -- stdlib or a
    dependency). Tries two shapes, both legitimate for `from X import Y`:
    X itself being a module (`from app.services import auth_service` where
    auth_service is a submodule), and X.Y being one (`from app.services.auth_service
    import AuthService`, where the caller already folds the class name into
    imported_symbol rather than source_module -- but some parsers might not,
    so both are checked)."""
    if source_module in module_index:
        return module_index[source_module]
    combined = f"{source_module}.{imported_symbol}" if source_module else imported_symbol
    return module_index.get(combined)
