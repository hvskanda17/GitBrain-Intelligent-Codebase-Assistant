import uuid

from app.services.embedding_service import EmbeddingService, _batched


def test_batched_splits_into_correct_sizes():
    items = list(range(10))
    batches = list(_batched(items, 3))
    assert batches == [[0, 1, 2], [3, 4, 5], [6, 7, 8], [9]]


def test_batched_single_batch_when_smaller_than_size():
    assert list(_batched([1, 2], 10)) == [[1, 2]]


def test_batched_empty_input_yields_no_batches():
    assert list(_batched([], 5)) == []


def test_batched_exact_multiple_of_batch_size():
    items = list(range(6))
    batches = list(_batched(items, 3))
    assert batches == [[0, 1, 2], [3, 4, 5]]


def test_generate_embeddings_skips_gracefully_with_no_client_configured():
    # client=None is the "no API key configured" case -- this must return 0
    # without ever touching the session (session=None here proves it: if the
    # session were touched, this would crash rather than return cleanly).
    service = EmbeddingService(session=None, client=None)
    result = service.generate_embeddings(uuid.uuid4())
    assert result == 0
