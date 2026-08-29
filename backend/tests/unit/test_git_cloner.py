import subprocess
from pathlib import Path

import pytest

from app.ingestion.git_cloner import GitCloneError, clone_repository


@pytest.fixture
def local_git_remote(tmp_path: Path) -> Path:
    """A real, tiny git repo on local disk, standing in for a remote -- clone_repository
    doesn't know or care that the URL is a local path instead of https://github.com/...,
    which is what makes this a genuine test of the clone logic without needing network."""
    remote = tmp_path / "remote_repo"
    remote.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=remote, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=remote, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=remote, check=True)
    (remote / "README.md").write_text("hello\n")
    subprocess.run(["git", "add", "."], cwd=remote, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "initial"], cwd=remote, check=True)
    return remote


def test_clone_repository_succeeds_and_returns_commit_hash(local_git_remote: Path, tmp_path: Path):
    destination = tmp_path / "clone_target"
    commit_hash = clone_repository(str(local_git_remote), destination, allowed_protocols="http:https:file")

    assert (destination / "README.md").exists()
    assert len(commit_hash) == 40  # full sha1 hex


def test_clone_repository_wipes_existing_destination(local_git_remote: Path, tmp_path: Path):
    destination = tmp_path / "clone_target"
    destination.mkdir()
    (destination / "stale_file.txt").write_text("leftover from a previous attempt")

    clone_repository(str(local_git_remote), destination, allowed_protocols="http:https:file")

    assert not (destination / "stale_file.txt").exists()
    assert (destination / "README.md").exists()


def test_clone_repository_raises_on_nonexistent_remote(tmp_path: Path):
    with pytest.raises(GitCloneError):
        clone_repository(
            str(tmp_path / "does_not_exist"), tmp_path / "clone_target", allowed_protocols="http:https:file"
        )


def test_rejects_disallowed_protocol_by_default(local_git_remote: Path, tmp_path: Path):
    """Confirms GIT_ALLOW_PROTOCOL is actually enforced -- this is what stops a
    malicious remote_url from using file:// or ext:: to read local files or execute
    commands. Uses the production default (http:https only, no override), so a bare
    local path -- which git treats as the file transport -- should be refused."""
    with pytest.raises(GitCloneError):
        clone_repository(str(local_git_remote), tmp_path / "clone_target")
