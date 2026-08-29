# GitBrain backend

FastAPI + PostgreSQL/pgvector + Redis + Celery. Covers **Phase 2** (app skeleton,
auth, core CRUD), **Phase 4** (ingestion: clone → detect languages → walk & hash
files), **Phase 5** (static analysis: parse each file, extract functions/classes/
methods/imports, resolve the call graph), **Phase 6** (knowledge graph: resolve
imports to real files, project everything into a generic node/edge graph, expose it
over the API), and **Phase 7** (hybrid retrieval: embed functions/classes, combine
lexical + vector + graph-expansion search via Reciprocal Rank Fusion, pack the
result into a token budget). Phase 3 (frontend) is a sibling package. Chat (the LLM
call that turns retrieved context into an actual answer) is Phase 8.

This is also the first phase where a repository can reach `status=ready` — the full
pipeline from the Phase 1 design now runs clone-to-ready.

## Local setup

```bash
cp .env.example .env          # edit JWT_SECRET_KEY at minimum; EMBEDDING_API_KEY
                               # if you want vector search (see below if you don't)
docker compose up -d postgres redis
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload          # terminal 1 -- the API
celery -A workers.celery_app worker --loglevel=info --queues=ingestion   # terminal 2 -- the worker
```

API docs: http://localhost:8000/docs

## Running everything in Docker

```bash
docker compose up --build
```

Starts `postgres`, `redis`, `api`, and `worker` — a dedicated Celery worker
consuming the `ingestion` queue, sharing a `gitbrain_repos_data` volume with the API
container so cloned repositories persist across worker restarts.

## Tests, and three real gaps worth reading before trusting this (Phases 5, 6, 7)

```bash
docker compose exec postgres createdb -U gitbrain gitbrain_test   # once
pytest
```

Almost everything in this project was executed and verified in the sandbox that
built it before being handed over. Three categories of piece weren't, because the
tools to run them genuinely weren't available there (no network, no Postgres) —
each is called out explicitly rather than left for you to discover:

**`app/parsers/` (Phase 5).** Neither `tree-sitter` nor any language grammar could
be installed (no network access), so the parsing logic in
`app/parsers/extractors/python_parser.py` was written and never run against a real
parser. The core tree-sitter API was checked against the current official
py-tree-sitter README rather than written from memory. Run
`tests/unit/test_python_parser_smoke.py` first, before anything else, once you can:
```bash
pip install tree-sitter tree-sitter-language-pack
pytest tests/unit/test_python_parser_smoke.py -v
```

**Recursive-CTE and raw-SQL queries (Phases 6, 7).** This sandbox has no
PostgreSQL instance at all (no `psql`, no way to `initdb` one), so
`app/graph/traversal_queries.py` (bounded-depth call-graph traversal),
`app/retrieval/lexical_search.py` (Postgres full-text search), and
`app/retrieval/vector_search.py` (pgvector cosine similarity) were never executed.
Worth calibrating differently from the tree-sitter gap, though: `WITH RECURSIVE`,
`tsvector`/`ts_rank_cd`, and pgvector's `<=>` operator are all stable, long-settled
syntax, not fast-moving library APIs. The vector search query in particular got
extra scrutiny before shipping — pgvector's text input format (`[v1,v2,...]`, no
whitespace) doesn't match Python's default `str(list)` output (which inserts `", "`
between elements), so the parameter is built explicitly rather than via `repr()`,
and the bind parameter carries an explicit `::vector` cast rather than relying on
implicit typing. Point real repository data at all three before trusting the
results.

**The embedding API call (Phase 7).** `app/embeddings/embedding_client.py`'s
`OpenAIEmbeddingClient` was never executed against a real API — no network access,
and no API key would be configured here even if there were. It's a small, standard
REST call (send texts, get vectors back in the same order), which is a different
risk profile than a tree-sitter query or a recursive CTE, but "hard to get wrong"
isn't "verified." What *is* genuinely tested is everything this project's own logic
does around that call: chunking (`app/embeddings/chunker.py`), batching, and the
deliberate graceful-skip when no `EMBEDDING_API_KEY` is configured
(`app/services/embedding_service.py`) — the last one verified by calling
`generate_embeddings()` with `session=None` and confirming it returns cleanly
without ever touching the database, which is the whole point: a missing API key
should never be able to crash the pipeline.

Everything else got the same treatment as every prior phase: actually run, not just
read. Full regression, every pure-Python test module in the project together: **77
tests passing** across 13 modules. Bugs caught this way, by phase:

- **Phase 5:** an off-by-one in line counting (a trailing newline counted as an
  extra line); a typo that would have thrown `AttributeError` on the first
  re-indexed file; a duplicate-registration pattern in call resolution that made
  any single, unambiguous same-named method look falsely ambiguous and silently
  drop out of the call graph.
- **Phase 6:** `KnowledgeGraphService._persist` special-cased the repository
  node's `ref_id` to `None`, contradicting what the (already-tested) pure graph
  builder actually produces for that node — caught by checking the pure
  function's real output before writing the code that consumes it.
- **Phase 7:** a dead, half-finished code fragment left in
  `RetrievalService._load_chunks` from an abandoned first attempt at the query —
  not a subtle logic error, just sloppy, caught on a re-read before it shipped.
- **Phases 5-7, infrastructure:** `celery_app.py`'s
  `autodiscover_tasks(["workers.tasks"])` was looking for a `workers.tasks.tasks`
  module (Django's one-file-per-app convention), which doesn't match this
  project's `ingestion.py`/`parsing.py`/`graph.py`/`embeddings.py` split — a real
  worker would have registered zero tasks and rejected every message as
  unrecognized. Fixed with an explicit, correctly-ordered import; re-verified
  end to end as each new task file was added, most recently confirming all six
  pipeline stages register and chain in the right order.

Integration tests hit a real Postgres (`gitbrain_test`), not a mock. Test isolation
is schema-per-session rather than per-test rollback right now (see
`tests/conftest.py`); if the suite grows large enough for that to matter, switch
`db_session` to a SAVEPOINT-based nested transaction that rolls back after every
test.

## What's real vs. what's a seam

- Auth, project & repository CRUD, ownership checks, RBAC: fully implemented and
  tested (Phase 2).
- Ingestion — clone (protocol-restricted, incremental by content hash), `.gitignore`-
  aware file walk: fully implemented and tested (Phase 4).
- Static analysis (Phase 5): Python-only parsing (see the gap above), two-pass call
  resolution. An ambiguous same-named match is left unresolved rather than guessed
  at.
- Knowledge graph (Phase 6): Python import resolution, a pure and fully-tested
  graph-construction function, four endpoints under `/repositories/{id}/graph/`.
- **Hybrid retrieval (Phase 7):** `POST /repositories/{id}/search/semantic` runs
  lexical search (Postgres full-text over function/class name, signature, and
  docstring — works with or without embeddings), vector search (pgvector cosine
  similarity — empty if no embedding API key is configured, not an error), and a
  one-hop knowledge-graph expansion from the top candidates of each, then fuses
  all three with Reciprocal Rank Fusion (`app/retrieval/fusion.py`, the standard
  Cormack/Clarke/Buettcher 2009 algorithm — this is the actual "hybrid" in hybrid
  RAG: three signals whose scores aren't on comparable scales, combined without
  needing them to be) and packs the result into a token budget
  (`app/retrieval/context_builder.py`, a 4-chars-per-token heuristic rather than a
  real tokenizer dependency). A separate cross-encoder reranking pass — mentioned
  in the Phase 1 design alongside fusion — was deliberately not added: it would
  need the same kind of external model call as embeddings, unverifiable here, and
  RRF already serves as the ranking mechanism. Documented as a future enhancement,
  not silently dropped.
- Embeddings only cover functions and classes right now (not files, READMEs, or
  commits, all mentioned in the Phase 1 design) — a reasonable-scope cut, not an
  oversight, since functions/classes are what Phase 5 actually extracts
  structured metadata for.
- **The pipeline reaches `status=ready`, finally** — whether or not an embedding
  API key is configured. A repository without one still has working lexical and
  graph search; a later reindex once `EMBEDDING_API_KEY` is set would pick up
  vector search too.
- Workers use a synchronous SQLAlchemy session (`app/db/sync_session.py`) rather
  than the API's async one — see `IngestionService`'s docstring for why. Reading
  results back out for the API (both the knowledge graph and retrieval) is a
  normal async request-path concern, though, since only *building* things is a
  worker-only job.
- The database migration (`alembic/versions/0001_baseline_schema.py`) creates the
  full 22-table schema from Phase 1. Every table Phase 2 and 4-7 actually write to
  now has a matching SQLAlchemy model; `documentation` and `chat_*` get theirs in
  Phase 8.
