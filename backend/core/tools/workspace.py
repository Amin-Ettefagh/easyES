"""Project workspace sandbox.

Every project gets an isolated directory under ``settings.WORKSPACES_ROOT``
(default ``data/workspaces/<project-id>/``). Tools that write files are confined
here — paths are resolved and checked so a tool can never escape the sandbox
with ``..`` or an absolute path (SECURITY.md: workspace isolation). This is the
demo's stand-in for a real sandbox (E2B/Firecracker); the seam is the same.
"""
from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings


class WorkspaceError(Exception):
    pass


class Workspace:
    def __init__(self, key: str):
        if not key:
            raise WorkspaceError("Workspace key is required")
        root = Path(getattr(settings, "WORKSPACES_ROOT", "data/workspaces"))
        self.root = (root / key).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative: str) -> Path:
        # Reject absolute paths and normalize, then verify the result is still
        # inside the sandbox root.
        candidate = (self.root / relative).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError(f"Path escapes workspace: {relative!r}") from exc
        return candidate

    def write(self, relative: str, content: str) -> str:
        path = self._resolve(relative)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return str(path.relative_to(self.root))

    def read(self, relative: str) -> str:
        path = self._resolve(relative)
        if not path.exists():
            raise WorkspaceError(f"No such file: {relative!r}")
        return path.read_text(encoding="utf-8")

    def list(self) -> list[str]:
        out: list[str] = []
        for dirpath, _dirs, files in os.walk(self.root):
            for name in files:
                full = Path(dirpath) / name
                out.append(str(full.relative_to(self.root)))
        return sorted(out)
