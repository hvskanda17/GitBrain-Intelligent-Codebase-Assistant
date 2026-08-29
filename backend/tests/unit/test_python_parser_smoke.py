"""Run this after `pip install tree-sitter tree-sitter-language-pack` -- neither
package could be installed in the environment that wrote app/parsers/, so unlike
every other test in this suite, this one was written but never executed. It's
designed to fail loudly and specifically (which assumption broke, not just "it
didn't work") if any node-type or field-name assumption in python_parser.py is
wrong against the real grammar.

    pip install tree-sitter tree-sitter-language-pack
    pytest tests/unit/test_python_parser_smoke.py -v
"""

from app.parsers.extractors.python_parser import PythonParser

SAMPLE_SOURCE = '''
import os
from typing import Optional as Opt

def add(a: int, b: int = 0) -> int:
    """Adds two numbers."""
    return a + b

async def fetch_data(url: str):
    result = await client.get(url)
    return result

class Repository:
    """Base repository."""

    def __init__(self, session):
        self.session = session

    def save(self, entity):
        validate(entity)
        self.session.add(entity)
        return entity

    @staticmethod
    def build_key(entity_id):
        return format_key(entity_id)

    def _internal_helper(self):
        pass


class UserRepository(Repository):
    def save(self, entity):
        log_save(entity)
        return super().save(entity)
'''


def _parse():
    parser = PythonParser()
    tree = parser.parse_source(SAMPLE_SOURCE)
    return parser.extract(tree, SAMPLE_SOURCE)


def test_extracts_top_level_functions_with_signature_and_docstring():
    result = _parse()
    by_name = {f.name: f for f in result.functions}

    assert "add" in by_name, f"expected 'add' in {list(by_name)} -- function_definition/name field assumption is wrong"
    add = by_name["add"]
    assert add.return_type == "int", f"return_type was {add.return_type!r} -- return_type field assumption is wrong"
    assert add.docstring == "Adds two numbers.", f"docstring was {add.docstring!r}"
    assert [p.name for p in add.parameters] == ["a", "b"], add.parameters
    assert add.parameters[1].default == "0", add.parameters[1]
    assert add.parameters[0].type_annotation == "int", add.parameters[0]


def test_detects_async_functions():
    result = _parse()
    by_name = {f.name: f for f in result.functions}
    assert by_name["fetch_data"].is_async is True, (
        "is_async detection failed -- this is the lowest-confidence check in the "
        "file (see _is_async's comment); if this fails, that's the first place to look"
    )
    assert by_name["add"].is_async is False


def test_extracts_classes_with_inheritance_and_methods():
    result = _parse()
    by_name = {c.name: c for c in result.classes}

    assert "Repository" in by_name and "UserRepository" in by_name
    assert by_name["UserRepository"].parent_class_name == "Repository", (
        f"parent was {by_name['UserRepository'].parent_class_name!r} -- superclasses field assumption is wrong"
    )

    repo_methods = {m.name: m for m in by_name["Repository"].methods}
    assert set(repo_methods) == {"__init__", "save", "build_key", "_internal_helper"}
    assert repo_methods["build_key"].is_static is True, "staticmethod decorator detection failed"
    assert repo_methods["save"].is_static is False
    assert repo_methods["_internal_helper"].visibility == "protected"
    assert repo_methods["__init__"].visibility == "public"  # dunder is public by convention here


def test_extracts_imports_including_aliased():
    result = _parse()
    modules = {i.imported_symbol: i for i in result.imports}
    assert "os" in modules
    assert "Optional" in modules, f"aliased_import extraction failed -- got {list(modules)}"
    assert modules["Optional"].alias == "Opt"


def test_attributes_calls_to_the_correct_enclosing_function_or_method():
    result = _parse()
    by_caller: dict[str, list[str]] = {}
    for call in result.calls:
        by_caller.setdefault(call.caller_name, []).append(call.callee_name)

    assert "validate" in by_caller.get("Repository.save", []), by_caller
    assert "format_key" in by_caller.get("Repository.build_key", []), by_caller
    # UserRepository.save calls both log_save(...) and super().save(...) -- the
    # latter's callee_name should resolve to "save" via the attribute-node path
    assert "log_save" in by_caller.get("UserRepository.save", []), by_caller
    assert "save" in by_caller.get("UserRepository.save", []), (
        f"super().save(...) attribute-call extraction failed -- got {by_caller.get('UserRepository.save')}"
    )


if __name__ == "__main__":
    # Lets this run with a bare `python test_python_parser_smoke.py` too, not just pytest.
    test_extracts_top_level_functions_with_signature_and_docstring()
    test_detects_async_functions()
    test_extracts_classes_with_inheritance_and_methods()
    test_extracts_imports_including_aliased()
    test_attributes_calls_to_the_correct_enclosing_function_or_method()
    print("All python_parser smoke checks passed against a real tree-sitter parser.")
