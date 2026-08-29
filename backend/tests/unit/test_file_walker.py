from pathlib import Path

from app.ingestion.file_walker import walk_repository


def _write(path: Path, content: str | bytes = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(content)


def test_walks_files_and_computes_hash_and_loc(tmp_path: Path):
    _write(tmp_path / "main.py", "print('hi')\nprint('bye')\n")
    _write(tmp_path / "pkg" / "__init__.py", "")

    result = walk_repository(tmp_path)

    paths = {f.relative_path for f in result.files}
    assert paths == {"main.py", "pkg/__init__.py"}

    main = next(f for f in result.files if f.relative_path == "main.py")
    assert main.language == "python"
    assert main.loc == 2
    assert len(main.content_hash) == 64  # sha256 hex digest

    assert {d.relative_path for d in result.directories} == {"pkg"}


def test_loc_counts_lines_not_newlines_plus_one(tmp_path: Path):
    # A trailing newline is the normal, POSIX-correct file ending -- it must not be
    # counted as an extra blank line.
    _write(tmp_path / "with_trailing.py", "a = 1\nb = 2\n")
    _write(tmp_path / "no_trailing.py", b"a = 1\nb = 2")
    _write(tmp_path / "empty.py", b"")

    result = walk_repository(tmp_path)
    by_path = {f.relative_path: f for f in result.files}

    assert by_path["with_trailing.py"].loc == 2
    assert by_path["no_trailing.py"].loc == 2
    assert by_path["empty.py"].loc == 0


def test_respects_root_gitignore(tmp_path: Path):
    _write(tmp_path / ".gitignore", "*.log\nbuild/\n")
    _write(tmp_path / "app.py", "x = 1\n")
    _write(tmp_path / "debug.log", "noise")
    _write(tmp_path / "build" / "output.txt", "compiled")

    result = walk_repository(tmp_path)

    assert {f.relative_path for f in result.files} == {"app.py", ".gitignore"}


def test_respects_nested_gitignore(tmp_path: Path):
    _write(tmp_path / "frontend" / ".gitignore", "dist/\n")
    _write(tmp_path / "frontend" / "src" / "index.ts", "export {}\n")
    _write(tmp_path / "frontend" / "dist" / "index.js", "compiled")

    result = walk_repository(tmp_path)

    paths = {f.relative_path for f in result.files}
    assert "frontend/src/index.ts" in paths
    assert not any(p.startswith("frontend/dist") for p in paths)


def test_always_ignores_node_modules_and_git_regardless_of_gitignore(tmp_path: Path):
    _write(tmp_path / "node_modules" / "left-pad" / "index.js", "module.exports = 1;")
    _write(tmp_path / ".git" / "HEAD", "ref: refs/heads/main")
    _write(tmp_path / "app.js", "console.log(1)")

    result = walk_repository(tmp_path)

    assert {f.relative_path for f in result.files} == {"app.js"}


def test_flags_test_files_by_path_convention(tmp_path: Path):
    _write(tmp_path / "src" / "math.py", "def add(a, b): return a + b\n")
    _write(tmp_path / "tests" / "test_math.py", "def test_add(): pass\n")

    result = walk_repository(tmp_path)
    by_path = {f.relative_path: f for f in result.files}

    assert by_path["tests/test_math.py"].is_test_file is True
    assert by_path["src/math.py"].is_test_file is False
