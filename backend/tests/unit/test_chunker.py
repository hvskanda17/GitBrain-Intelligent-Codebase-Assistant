from app.embeddings.chunker import MAX_CHUNK_CHARS, chunk_class, chunk_function


def test_chunk_function_includes_name_signature_and_docstring():
    chunk = chunk_function(
        source_id="fn-1",
        name="create_order",
        qualified_name="OrderService.create_order",
        signature="def create_order(self, items: list[Item]) -> Order",
        docstring="Creates a new order from a list of items.",
        is_async=False,
    )
    assert chunk.source_type == "function"
    assert chunk.source_id == "fn-1"
    assert "OrderService.create_order" in chunk.chunk_text
    assert "def create_order" in chunk.chunk_text
    assert "Creates a new order" in chunk.chunk_text


def test_chunk_function_marks_async():
    chunk = chunk_function(
        source_id="fn-1", name="fetch", qualified_name=None, signature="def fetch()", docstring=None, is_async=True
    )
    assert chunk.chunk_text.startswith("async function fetch")


def test_chunk_function_falls_back_to_bare_name_without_qualified_name():
    chunk = chunk_function(
        source_id="fn-1", name="helper", qualified_name=None, signature=None, docstring=None, is_async=False
    )
    assert "function helper" in chunk.chunk_text


def test_chunk_function_handles_missing_docstring_and_signature():
    chunk = chunk_function(
        source_id="fn-1", name="helper", qualified_name="helper", signature=None, docstring=None, is_async=False
    )
    assert chunk.chunk_text == "function helper"


def test_chunk_function_truncates_to_max_length():
    huge_docstring = "x" * (MAX_CHUNK_CHARS * 2)
    chunk = chunk_function(
        source_id="fn-1", name="f", qualified_name="f", signature="def f()", docstring=huge_docstring, is_async=False
    )
    assert len(chunk.chunk_text) == MAX_CHUNK_CHARS


def test_chunk_class_includes_name_docstring_and_methods():
    chunk = chunk_class(
        source_id="cls-1",
        name="OrderService",
        qualified_name="OrderService",
        docstring="Handles order lifecycle.",
        method_names=["create_order", "cancel_order"],
    )
    assert chunk.source_type == "class"
    assert "class OrderService" in chunk.chunk_text
    assert "Handles order lifecycle" in chunk.chunk_text
    assert "create_order" in chunk.chunk_text and "cancel_order" in chunk.chunk_text


def test_chunk_class_handles_no_methods_or_docstring():
    chunk = chunk_class(source_id="cls-1", name="Empty", qualified_name="Empty", docstring=None, method_names=[])
    assert chunk.chunk_text == "class Empty"
