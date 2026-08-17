"""Small, sandboxed Git service for each easyES workspace."""
from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path

from django.utils.text import slugify

from core.tools.workspace import Workspace

_locks: dict[str, threading.Lock] = {}


class WorkspaceGitError(Exception):
    pass


def _run(root: Path, *args: str, check: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, text=True, encoding="utf-8",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkspaceGitError(str(exc)) from exc
    if check and result.returncode:
        raise WorkspaceGitError(result.stderr.strip() or result.stdout.strip() or "Git command failed")
    return result.stdout.strip()


def ensure_repository(workspace_key: str) -> Path:
    root = Workspace(workspace_key).root
    if not (root / ".git").exists():
        _run(root, "init", "-b", "main")
        _run(root, "config", "user.name", "easyES")
        _run(root, "config", "user.email", "easyes@local")
    return root


def snapshot_artifact(artifact) -> str:
    """Write an artifact into the workspace and commit its exact output."""
    key = artifact.project.workspace_key
    lock = _locks.setdefault(key, threading.Lock())
    with lock:
        root = ensure_repository(key)
        ext = ".md" if artifact.content_type.startswith("text/") else ".txt"
        name = slugify(artifact.name)[:100] or str(artifact.uuid)
        relative = f"outputs/iteration-{artifact.iteration:03d}/{name}-{str(artifact.uuid)[:8]}{ext}"
        Workspace(key).write(relative, artifact.content)
        _run(root, "add", "--", relative)
        _run(root, "commit", "-m", f"artifact: {artifact.name} [{artifact.kind}]", check=False)
        return relative


def repository_state(workspace_key: str) -> dict:
    root = ensure_repository(workspace_key)
    branch = _run(root, "branch", "--show-current", check=False) or "main"
    status = _run(root, "status", "--short", check=False)
    history_raw = _run(root, "log", "--pretty=format:%H%x09%h%x09%aI%x09%an%x09%s", "-n", "100", check=False)
    commits = []
    for line in history_raw.splitlines():
        parts = line.split("\t", 4)
        if len(parts) == 5:
            commits.append(dict(zip(("hash", "short_hash", "date", "author", "message"), parts)))
    files = _run(root, "ls-files", check=False).splitlines()
    return {"initialized": True, "branch": branch, "dirty": bool(status), "status": status.splitlines(), "files": files, "commits": commits}


def repository_diff(workspace_key: str, revision: str = "HEAD") -> str:
    root = ensure_repository(workspace_key)
    safe_revision = revision if revision == "HEAD" or all(character.isalnum() or character in "-_~^" for character in revision) else "HEAD"
    return _run(root, "show", "--format=fuller", "--stat", "--patch", safe_revision, check=False)


def commit_workspace(workspace_key: str, message: str) -> dict:
    root = ensure_repository(workspace_key)
    _run(root, "add", "--all")
    _run(root, "commit", "-m", message[:200] or "Workspace checkpoint", check=False)
    return repository_state(workspace_key)
