"""Flags functions/methods that are never called and never exported. Precision
caveats are real and worth stating rather than glossing over: this can't see calls
made through reflection, dynamic dispatch, string-based lookups (`getattr(obj,
name)()`), or a framework that invokes something by convention (a test runner
calling every `test_*` function, a web framework calling a route handler it
discovered by decorator). It's a lead worth surfacing to a human, not a
delete-with-confidence signal -- which is exactly how it's framed in the API
response (Phase 6+): as a flagged candidate, not an automatic action.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class CallableInfo:
    id: str
    name: str
    is_exported: bool
    is_test_file: bool


def find_dead_code(
    callables: list[CallableInfo],
    called_ids: set[str],
    *,
    entry_point_names: frozenset[str] = frozenset(
        {"main", "__init__", "__new__", "setup", "handler"}
    ),
) -> list[CallableInfo]:
    """A callable is flagged when it is: not called anywhere in the resolved call
    graph, not exported (an exported symbol may be an external API's entry point),
    not defined in a test file (test functions are invoked by the test runner, not
    by an explicit call site), and not named like a common framework/language entry
    point."""
    return [
        c
        for c in callables
        if c.id not in called_ids
        and not c.is_exported
        and not c.is_test_file
        and c.name not in entry_point_names
    ]
