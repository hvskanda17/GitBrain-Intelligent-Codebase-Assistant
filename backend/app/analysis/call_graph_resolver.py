"""Resolves raw call data (a caller name and a callee name, as extracted by any
language parser) into call-graph edges: matched to a known function/method where
possible, or left as an unresolved raw name (a call through a variable, a
dynamically-dispatched method, or -- the common case -- a callee defined in a file
that hasn't been parsed yet). Deliberately language-agnostic and DB-agnostic -- it
operates on plain dicts and dataclasses, not ORM rows or tree-sitter nodes, which is
what makes it fully testable without a parser or a database.

Two callers use this: app/services/analysis_service.py's parse_file() resolves
same-file calls immediately (the caller is always known -- it's in the file just
parsed), and its build_call_graph() makes a second, repository-wide pass afterward
using CallableIndex directly, to resolve calls whose callee lives in a different
file that wasn't parsed yet at the time.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnownCallable:
    """A function or method known within some resolution scope (a single file, or a
    whole repository once every file has been parsed)."""

    id: str
    name: str
    qualified_name: str | None = None


@dataclass(frozen=True)
class ResolvedCall:
    caller_id: str
    callee_id: str | None
    callee_raw_name: str
    line_number: int


class CallableIndex:
    """Precomputed qualified-name and bare-name lookup over a callable pool, so
    resolving many calls against the same pool (either within one file or across a
    whole repository) doesn't rebuild the indices per call."""

    def __init__(self, callables: list[KnownCallable]) -> None:
        self._by_qualified = {c.qualified_name: c for c in callables if c.qualified_name}
        self._by_bare_name: dict[str, list[KnownCallable]] = {}
        for c in callables:
            self._by_bare_name.setdefault(c.name, []).append(c)

    def match(self, name: str) -> KnownCallable | None:
        """Prefers an exact qualified-name match, falls back to bare-name only when
        it's unambiguous, and otherwise returns None -- ambiguous bare-name matches
        (two different classes each with a method called `save`) are intentionally
        NOT guessed at; a wrong resolved edge is worse than an honestly-unresolved
        one, since later retrieval will trust these edges as ground truth."""
        if name in self._by_qualified:
            return self._by_qualified[name]
        candidates = self._by_bare_name.get(name, [])
        return candidates[0] if len(candidates) == 1 else None


def resolve_calls(
    calls: list[tuple[str, str, int]],
    caller_ids_by_name: dict[str, str],
    callables: list[KnownCallable],
) -> list[ResolvedCall]:
    """`calls` is (caller_name, callee_name, line_number) triples, exactly what a
    parser's extract() produces before any IDs exist. `caller_ids_by_name` maps a
    caller's name to its already-persisted id (functions/methods are inserted before
    call resolution runs, so this is always available)."""
    index = CallableIndex(callables)

    resolved: list[ResolvedCall] = []
    for caller_name, callee_name, line_number in calls:
        caller_id = caller_ids_by_name.get(caller_name)
        if caller_id is None:
            continue  # a call from an unknown caller (e.g. module-level code) -- skip

        match = index.match(callee_name)
        resolved.append(
            ResolvedCall(
                caller_id=caller_id,
                callee_id=match.id if match else None,
                callee_raw_name=callee_name,
                line_number=line_number,
            )
        )

    return resolved
