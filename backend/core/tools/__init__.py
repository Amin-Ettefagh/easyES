"""Tool runtime: the allow-listed operations agents may invoke.

A Tool row (apps.tools.Tool) names a handler registered here. Agents can only
call tools they have been granted (apps.agents.AgentToolGrant) — the engine
checks the grant before dispatching, so there is no path to arbitrary shell
(SECURITY.md). The built-in handlers are deliberately small and safe; every one
operates through the project :class:`~core.tools.workspace.Workspace` sandbox.
"""
from __future__ import annotations

from typing import Callable

from core.tools.workspace import Workspace

_HANDLERS: dict[str, Callable] = {}


class ToolError(Exception):
    pass


def register(name: str):
    def deco(fn: Callable) -> Callable:
        _HANDLERS[name] = fn
        return fn

    return deco


def get_handler(name: str) -> Callable:
    handler = _HANDLERS.get(name)
    if handler is None:
        raise ToolError(f"Unknown tool handler: {name!r}")
    return handler


def available() -> list[str]:
    return sorted(_HANDLERS)


# -- built-in handlers -----------------------------------------------------
@register("workspace.write")
def _workspace_write(*, workspace_key: str, path: str, content: str, **_) -> dict:
    ws = Workspace(workspace_key)
    written = ws.write(path, content)
    return {"path": written, "bytes": len(content)}


@register("workspace.read")
def _workspace_read(*, workspace_key: str, path: str, **_) -> dict:
    ws = Workspace(workspace_key)
    return {"path": path, "content": ws.read(path)}


@register("workspace.list")
def _workspace_list(*, workspace_key: str, **_) -> dict:
    ws = Workspace(workspace_key)
    return {"files": ws.list()}


@register("echo")
def _echo(*, text: str = "", **_) -> dict:
    """A no-op tool used in tests and as a safe default."""
    return {"text": text}
