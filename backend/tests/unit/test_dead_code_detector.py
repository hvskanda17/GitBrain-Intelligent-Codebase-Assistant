from app.analysis.dead_code_detector import CallableInfo, find_dead_code


def test_uncalled_private_function_is_flagged():
    callables = [CallableInfo(id="1", name="helper", is_exported=False, is_test_file=False)]
    dead = find_dead_code(callables, called_ids=set())
    assert [c.id for c in dead] == ["1"]


def test_called_function_is_not_flagged():
    callables = [CallableInfo(id="2", name="used_fn", is_exported=False, is_test_file=False)]
    dead = find_dead_code(callables, called_ids={"2"})
    assert dead == []


def test_exported_function_is_not_flagged_even_if_uncalled():
    # An exported symbol may be an external API's entry point -- never seeing a
    # call site inside this repo doesn't mean nothing uses it.
    callables = [CallableInfo(id="3", name="public_api", is_exported=True, is_test_file=False)]
    dead = find_dead_code(callables, called_ids=set())
    assert dead == []


def test_test_file_function_is_not_flagged():
    # Test functions are invoked by the test runner, not by an explicit call site
    # this project's call graph would ever see.
    callables = [CallableInfo(id="4", name="test_something", is_exported=False, is_test_file=True)]
    dead = find_dead_code(callables, called_ids=set())
    assert dead == []


def test_entry_point_names_are_not_flagged():
    callables = [CallableInfo(id="5", name="main", is_exported=False, is_test_file=False)]
    dead = find_dead_code(callables, called_ids=set())
    assert dead == []


def test_mixed_set_flags_only_the_genuinely_dead_one():
    callables = [
        CallableInfo(id="1", name="helper", is_exported=False, is_test_file=False),
        CallableInfo(id="2", name="used_fn", is_exported=False, is_test_file=False),
        CallableInfo(id="3", name="public_api", is_exported=True, is_test_file=False),
        CallableInfo(id="4", name="test_something", is_exported=False, is_test_file=True),
        CallableInfo(id="5", name="main", is_exported=False, is_test_file=False),
    ]
    dead = find_dead_code(callables, called_ids={"2"})
    assert [c.id for c in dead] == ["1"]
