from app.analysis.call_graph_resolver import CallableIndex, KnownCallable, resolve_calls


def test_unambiguous_bare_name_resolves():
    index = CallableIndex([KnownCallable(id="fn-validate", name="validate", qualified_name="validate")])
    match = index.match("validate")
    assert match is not None and match.id == "fn-validate"


def test_ambiguous_bare_name_is_not_guessed():
    # Two different classes, each with a method called "save" -- this is the exact
    # shape of bug analysis_service.py hit during development: a naive same-file
    # callable dict that registers each method under both its qualified AND bare
    # name made CallableIndex see duplicate entries, which made even a genuinely
    # unique method look ambiguous. This test (and test_persist_calls-style
    # coverage in analysis_service's own construction) is what would catch a
    # regression back to that pattern.
    index = CallableIndex(
        [
            KnownCallable(id="m-save1", name="save", qualified_name="Repository.save"),
            KnownCallable(id="m-save2", name="save", qualified_name="UserRepository.save"),
        ]
    )
    assert index.match("save") is None
    # but the qualified name always resolves unambiguously
    assert index.match("UserRepository.save").id == "m-save2"


def test_single_registration_per_callable_is_not_falsely_ambiguous():
    # The regression case directly: exactly one "save" method should resolve by
    # bare name, not be treated as ambiguous just because it also has a qualified
    # name registered.
    index = CallableIndex([KnownCallable(id="m-save1", name="save", qualified_name="Repository.save")])
    match = index.match("save")
    assert match is not None and match.id == "m-save1"


def test_resolve_calls_end_to_end():
    callables = [
        KnownCallable(id="fn-save", name="save", qualified_name="Repository.save"),
        KnownCallable(id="fn-save2", name="save", qualified_name="UserRepository.save"),
        KnownCallable(id="fn-validate", name="validate", qualified_name="validate"),
    ]
    caller_ids = {"Repository.save": "fn-save", "UserRepository.save": "fn-save2"}
    calls = [
        ("Repository.save", "validate", 10),           # unambiguous -> resolves
        ("UserRepository.save", "save", 20),            # ambiguous -> unresolved, raw name kept
        ("Repository.save", "some_dynamic_thing", 30),  # no match at all -> unresolved raw name kept
        ("unknown_caller", "validate", 40),             # caller not known -> dropped entirely
    ]

    resolved = resolve_calls(calls, caller_ids, callables)

    assert len(resolved) == 3
    assert resolved[0].callee_id == "fn-validate"
    assert resolved[1].callee_id is None and resolved[1].callee_raw_name == "save"
    assert resolved[2].callee_id is None and resolved[2].callee_raw_name == "some_dynamic_thing"
