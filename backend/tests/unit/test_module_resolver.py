from app.graph.module_resolver import ResolvableFile, build_module_path_index, compute_module_path, resolve_import


def test_computes_module_path_for_a_plain_file():
    assert compute_module_path("app/services/auth_service.py") == "app.services.auth_service"


def test_init_py_maps_to_its_containing_package():
    assert compute_module_path("app/services/__init__.py") == "app.services"


def test_root_level_init_py_is_not_a_resolvable_module():
    # An empty-string module path is never what a real `source_module` in an
    # import statement would contain, so treating this as unresolvable (None)
    # rather than manufacturing "" is the more useful contract -- nothing would
    # ever match against "" anyway.
    assert compute_module_path("__init__.py") is None


def test_root_level_file_has_no_directory_prefix():
    assert compute_module_path("main.py") == "main"


def test_non_python_file_returns_none():
    assert compute_module_path("README.md") is None
    assert compute_module_path("app/config.json") is None


def test_build_module_path_index_only_includes_python_files():
    files = [
        ResolvableFile(id="f1", path="app/services/auth_service.py", language="python"),
        ResolvableFile(id="f2", path="frontend/src/index.ts", language="typescript"),
        ResolvableFile(id="f3", path="README.md", language=None),
    ]
    index = build_module_path_index(files)
    assert index == {"app.services.auth_service": "f1"}


def test_resolve_import_matches_exact_module_path():
    index = {"app.services.auth_service": "f1"}
    assert resolve_import("app.services.auth_service", "AuthService", index) == "f1"


def test_resolve_import_matches_submodule_import_shape():
    # from app.services import auth_service -- source_module is the package,
    # imported_symbol is the submodule name.
    index = {"app.services.auth_service": "f1"}
    assert resolve_import("app.services", "auth_service", index) == "f1"


def test_resolve_import_returns_none_for_external_package():
    index = {"app.services.auth_service": "f1"}
    assert resolve_import("fastapi", "FastAPI", index) is None
    assert resolve_import("os", "path", index) is None


def test_resolve_import_handles_empty_source_module():
    # A plain `import foo` (no "from") parses with an empty-ish source_module in
    # some shapes -- make sure this doesn't crash on string formatting.
    index = {"foo": "f1"}
    assert resolve_import("", "foo", index) == "f1"
