"""Walks a cloned repository, respecting .gitignore at every level plus a baseline
of build/dependency folders that get skipped even in repos with an incomplete
.gitignore, and returns per-file metadata (path, language, hash, size, loc)."""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import pathspec

from app.ingestion.language_detector import detect_language

ALWAYS_IGNORED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", "target", "vendor", ".tox",
    ".pytest_cache", ".mypy_cache", ".turbo", "coverage", ".idea", ".vscode",
}
TEST_PATH_MARKERS = ("test_", "_test.", "/tests/", "/test/", ".test.", ".spec.")
GENERATED_MARKERS = ("/generated/", ".generated.", "/.next/", "/dist/", "/build/")


@dataclass
class WalkedFile:
    absolute_path: Path
    relative_path: str
    filename: str
    extension: str | None
    language: str | None
    content_hash: str
    size_bytes: int
    loc: int
    is_test_file: bool
    is_generated: bool


@dataclass
class WalkedDirectory:
    relative_path: str
    name: str
    parent_relative_path: str | None


@dataclass
class WalkResult:
    files: list[WalkedFile] = field(default_factory=list)
    directories: list[WalkedDirectory] = field(default_factory=list)


def _load_gitignore_specs(root: Path) -> list[tuple[Path, pathspec.PathSpec]]:
    """Collects every .gitignore in the tree, paired with the directory it applies
    to. Patterns are matched relative to that directory, which handles the common
    monorepo case (a root .gitignore plus per-package ones) reasonably well. Git's
    exact precedence rules for negation patterns across nested boundaries are
    subtler than this -- a documented simplification, not a full re-implementation
    of git's own matching engine."""
    specs: list[tuple[Path, pathspec.PathSpec]] = []
    for gitignore_path in root.rglob(".gitignore"):
        if any(part in ALWAYS_IGNORED_DIRS for part in gitignore_path.relative_to(root).parts):
            continue
        lines = gitignore_path.read_text(errors="ignore").splitlines()
        specs.append((gitignore_path.parent, pathspec.PathSpec.from_lines("gitwildmatch", lines)))
    return specs


def _is_ignored(path: Path, root: Path, specs: list[tuple[Path, pathspec.PathSpec]]) -> bool:
    if any(part in ALWAYS_IGNORED_DIRS for part in path.relative_to(root).parts):
        return True
    for spec_dir, spec in specs:
        try:
            rel = path.relative_to(spec_dir)
        except ValueError:
            continue
        if spec.match_file(str(rel)):
            return True
    return False


def walk_repository(root: Path) -> WalkResult:
    result = WalkResult()
    specs = _load_gitignore_specs(root)

    for current_dir, dirnames, filenames in root.walk():
        rel_dir = str(current_dir.relative_to(root)) if current_dir != root else ""

        dirnames[:] = [d for d in dirnames if not _is_ignored(current_dir / d, root, specs)]

        if rel_dir:
            result.directories.append(
                WalkedDirectory(
                    relative_path=rel_dir,
                    name=current_dir.name,
                    parent_relative_path=(
                        str(current_dir.parent.relative_to(root)) if current_dir.parent != root else None
                    ),
                )
            )

        for filename in filenames:
            file_path = current_dir / filename
            if _is_ignored(file_path, root, specs):
                continue
            try:
                content = file_path.read_bytes()
            except OSError:
                continue

            rel_path = str(file_path.relative_to(root))
            result.files.append(
                WalkedFile(
                    absolute_path=file_path,
                    relative_path=rel_path,
                    filename=filename,
                    extension=file_path.suffix or None,
                    language=detect_language(filename),
                    content_hash=hashlib.sha256(content).hexdigest(),
                    size_bytes=len(content),
                    loc=_count_lines(content),
                    is_test_file=any(marker in f"/{rel_path.lower()}" for marker in TEST_PATH_MARKERS),
                    is_generated=any(
                        marker in f"/{rel_path.lower()}/" for marker in GENERATED_MARKERS
                    ),
                )
            )

    return result


def _count_lines(content: bytes) -> int:
    """Counting '\\n' + 1 overcounts by one for the (normal, POSIX-correct) case of
    a file ending in a trailing newline -- 'a\\nb\\n' is 2 lines, not 3."""
    if not content:
        return 0
    if content.endswith(b"\n"):
        return content.count(b"\n")
    return content.count(b"\n") + 1
