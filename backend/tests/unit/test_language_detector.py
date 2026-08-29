from app.ingestion.language_detector import detect_language, detect_primary_language


def test_detects_common_extensions():
    assert detect_language("main.py") == "python"
    assert detect_language("App.tsx") == "typescript"
    assert detect_language("index.js") == "javascript"
    assert detect_language("Main.java") == "java"
    assert detect_language("lib.rs") == "rust"
    assert detect_language("server.go") == "go"


def test_returns_none_for_unrecognized_extension():
    assert detect_language("README.md") is None
    assert detect_language("Makefile") is None
    assert detect_language("noextension") is None


def test_primary_language_is_majority_by_file_count():
    assert detect_primary_language({"python": 40, "javascript": 12}) == "python"
    assert detect_primary_language({}) is None
    assert detect_primary_language({"go": 1}) == "go"
