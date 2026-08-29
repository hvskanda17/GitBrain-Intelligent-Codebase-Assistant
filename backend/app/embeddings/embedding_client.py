"""Calls an embedding API. Sync, matching every other worker-side piece in this
project (see IngestionService's docstring for why workers stay sync) -- this is
genuinely how it gets called from generate_embeddings, a Celery task.

Verification note: never executed against a real API in this environment -- no
network access, and no API key would be configured here even if there were.
Structurally this is a small, standard REST call (send texts, get vectors back in
the same order), the kind of integration that's hard to get subtly wrong the way a
tree-sitter query or a recursive CTE can be -- but "hard to get wrong" isn't
"verified," and it's called out here for the same reason every other unexecuted
piece in this project is: so it's obvious what to distrust rather than a surprise
later. The interface (EmbeddingClient) is what everything else in app/embeddings/
and app/services/embedding_service.py actually depends on, which is what makes it
possible to test the surrounding chunking/batching/persistence logic for real (see
tests/unit/test_embedding_service.py) without needing the real API at all.
"""

from typing import Protocol

import httpx


class EmbeddingClient(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingClient:
    def __init__(self, api_key: str, model: str, dimensions: int, base_url: str) -> None:
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions
        self.base_url = base_url.rstrip("/")

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": self.model, "input": texts, "dimensions": self.dimensions},
            )
            response.raise_for_status()
            data = response.json()["data"]
            # The API documents in-order results, but sorting by the index it
            # actually returns guarantees the mapping back to `texts` rather than
            # assuming an ordering contract holds.
            return [item["embedding"] for item in sorted(data, key=lambda item: item["index"])]
