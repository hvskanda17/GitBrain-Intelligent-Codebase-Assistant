"""Clones a remote repository to local disk.

Security note: git supports URL schemes (`ext::`, `file://`, and historically
crafted `ssh://` variants) that can be abused to execute arbitrary commands or read
arbitrary local files when the URL is attacker-controlled -- and a repository URL
submitted through a public form is exactly that. GIT_ALLOW_PROTOCOL restricts git
itself to the protocols this app intends to support (http/https by default), which
is the documented, correct mitigation (this is the same class of issue behind
CVE-2017-1000117 and later `ext::`/`file://` abuses) -- enforced at the git
subprocess level rather than trying to out-regex every malicious URL shape.

Only public repositories are supported right now -- there's no credential storage
or injection yet, and GIT_TERMINAL_PROMPT=0 makes a private repo fail fast instead
of hanging, rather than silently waiting for a password that will never come.
"""

import os
import shutil
import subprocess
from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


class GitCloneError(Exception):
    pass


def clone_repository(
    remote_url: str,
    destination: Path,
    *,
    branch: str | None = None,
    allowed_protocols: str | None = None,
) -> str:
    """Shallow-clones `remote_url` into `destination` (wiping any prior contents),
    and returns the resolved HEAD commit hash. Raises GitCloneError on failure,
    including a URL whose protocol isn't in `allowed_protocols` (defaults to
    settings.GIT_ALLOWED_PROTOCOLS, i.e. http/https only)."""
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [remote_url, str(destination)]

    # Inherit the base environment (PATH, HOME, etc. -- git can misbehave without
    # them) and layer the two security-relevant overrides on top, rather than
    # replacing the environment wholesale.
    env = {
        **os.environ,
        "GIT_ALLOW_PROTOCOL": allowed_protocols or settings.GIT_ALLOWED_PROTOCOLS,
        "GIT_TERMINAL_PROMPT": "0",
    }

    try:
        subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=settings.GIT_CLONE_TIMEOUT_SECONDS,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        raise GitCloneError(f"git clone failed: {exc.stderr.strip()[:500]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitCloneError(f"git clone timed out after {settings.GIT_CLONE_TIMEOUT_SECONDS}s") from exc

    return _current_commit_hash(destination)


def _current_commit_hash(repo_path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()
