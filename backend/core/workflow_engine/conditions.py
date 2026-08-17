"""Safe boolean expression evaluator for edge/branch conditions.

Workflow edges may carry a condition like ``evaluation.passed == True`` or
``iteration >= 3``. We evaluate these against the run context using Python's
``ast`` module in a *restricted* mode: only literals, names, comparisons,
boolean/unary ops, and attribute/subscript access on the provided namespace are
allowed. No calls, no attribute access on arbitrary objects, no imports — so a
malicious or malformed condition can never execute code (SECURITY.md).

An empty condition is treated as ``True`` (an unconditional edge).
"""
from __future__ import annotations

import ast
import operator
from typing import Any

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
}

_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}

_UNARY_OPS = {
    ast.Not: operator.not_,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class ConditionError(Exception):
    pass


class _Namespace(dict):
    """dict that also supports attribute access, so ``evaluation.passed`` and
    ``evaluation['passed']`` both work in expressions."""

    def __getattr__(self, item):
        try:
            value = self[item]
        except KeyError as exc:  # pragma: no cover - defensive
            raise ConditionError(f"Unknown name: {item}") from exc
        if isinstance(value, dict):
            return _Namespace(value)
        return value


def _eval(node: ast.AST, ns: _Namespace) -> Any:
    if isinstance(node, ast.Expression):
        return _eval(node.body, ns)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ns:
            return ns[node.id]
        raise ConditionError(f"Unknown name: {node.id}")
    if isinstance(node, ast.Attribute):
        value = _eval(node.value, ns)
        if isinstance(value, dict):
            wrapped = _Namespace(value)
            if node.attr in wrapped:
                return wrapped[node.attr]
        raise ConditionError(f"Unknown attribute: {node.attr}")
    if isinstance(node, ast.Subscript):
        value = _eval(node.value, ns)
        key = _eval(node.slice, ns)
        try:
            return value[key]
        except (KeyError, IndexError, TypeError) as exc:
            raise ConditionError(f"Bad subscript: {key}") from exc
    if isinstance(node, ast.BoolOp):
        values = [_eval(v, ns) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        return any(values)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand, ns))
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left, ns), _eval(node.right, ns))
    if isinstance(node, ast.Compare):
        left = _eval(node.left, ns)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval(comparator, ns)
            func = _CMP_OPS.get(type(op))
            if func is None:
                raise ConditionError(f"Unsupported comparison: {op}")
            if not func(left, right):
                return False
            left = right
        return True
    if isinstance(node, (ast.List, ast.Tuple)):
        return [_eval(e, ns) for e in node.elts]
    raise ConditionError(f"Unsupported expression element: {type(node).__name__}")


def evaluate(expression: str, namespace: dict) -> bool:
    """Evaluate ``expression`` against ``namespace`` and return a bool.

    Empty/whitespace expressions are unconditional (True). Any parse or lookup
    error raises :class:`ConditionError`, which the engine treats as a false
    branch (and logs) rather than crashing the run.
    """
    if not expression or not expression.strip():
        return True
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError as exc:
        raise ConditionError(f"Invalid condition syntax: {expression!r}") from exc
    return bool(_eval(tree, _Namespace(namespace)))
