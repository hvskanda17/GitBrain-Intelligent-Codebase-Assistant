"""Sync service used by Celery worker tasks (see workers/tasks/ingestion.py).

Ingestion runs on a synchronous SQLAlchemy engine (app/db/sync_session.py),
deliberately separate from the async engine the FastAPI app uses -- Celery's
execution model is fundamentally synchronous per task, and bridging into asyncio
from inside a possibly-prefork'd worker process is a well-known source of subtle
bugs around event-loop lifecycle and asyncpg's fork-unsafety. A second, boring,
synchronous DB path avoids that whole class of problem.
"""

from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.models.filesystem import Directory, File
from app.db.models.repository import IndexingStatus, Repository
from app.ingestion.file_walker import walk_repository
from app.ingestion.git_cloner import GitCloneError, clone_repository
from app.ingestion.language_detector import detect_primary_language

logger = get_logger(__name__)
settings = get_settings()


class IngestionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def clone(self, repository_id: UUID) -> None:
        repository = self._get_repository(repository_id)
        self._set_status(repository, IndexingStatus.CLONING)

        local_path = Path(settings.REPO_STORAGE_PATH) / str(repository_id)
        try:
            commit_hash = clone_repository(repository.remote_url, local_path, branch=repository.default_branch)
        except GitCloneError as exc:
            logger.error("ingestion.clone.failed repository_id=%s error=%s", repository_id, exc)
            self._set_status(repository, IndexingStatus.FAILED)
            raise

        repository.local_path = str(local_path)
        repository.last_indexed_commit_hash = commit_hash
        self.session.flush()

    def detect_and_walk(self, repository_id: UUID, *, force_full: bool = False) -> None:
        """Walks the freshly-cloned tree and, unless force_full, skips re-touching
        any file whose content_hash hasn't changed since the last run -- see
        backend/README.md for why re-cloning is still always "full" while file
        processing is incremental (the clone itself is cheap; the expensive part is
        everything Phase 5+ does per file, which is exactly what this preserves)."""
        repository = self._get_repository(repository_id)
        if not repository.local_path:
            raise ValueError(f"repository {repository_id} has no local_path -- clone must run first")

        self._set_status(repository, IndexingStatus.PARSING)

        walked = walk_repository(Path(repository.local_path))

        directory_ids = self._upsert_directories(repository_id, walked.directories)
        language_counts = self._upsert_files(
            repository_id, walked.files, directory_ids, force_full=force_full
        )

        repository.primary_language = detect_primary_language(language_counts)
        repository.stats = {
            "file_count": len(walked.files),
            "directory_count": len(walked.directories),
            "language_breakdown": language_counts,
        }
        # Genuinely honest stopping point: parsing (tree-sitter, Phase 5) hasn't
        # been built yet, so the pipeline can't claim "ready" -- it stops exactly
        # where Phase 4's responsibility ends, at status=parsing.
        self.session.flush()

    def _upsert_directories(
        self, repository_id: UUID, walked_directories: list
    ) -> dict[str, UUID]:
        existing = {
            d.path: d
            for d in self.session.scalars(
                select(Directory).where(Directory.repository_id == repository_id)
            )
        }
        directory_ids: dict[str, UUID] = {}

        for walked_dir in sorted(walked_directories, key=lambda d: d.relative_path.count("/")):
            row = existing.get(walked_dir.relative_path)
            if row is None:
                row = Directory(repository_id=repository_id, path=walked_dir.relative_path, name=walked_dir.name)
                self.session.add(row)
            row.parent_id = directory_ids.get(walked_dir.parent_relative_path or "")
            self.session.flush()
            directory_ids[walked_dir.relative_path] = row.id

        return directory_ids

    def _upsert_files(
        self,
        repository_id: UUID,
        walked_files: list,
        directory_ids: dict[str, UUID],
        *,
        force_full: bool,
    ) -> dict[str, int]:
        existing_files = {
            f.path: f
            for f in self.session.scalars(select(File).where(File.repository_id == repository_id))
        }
        seen_paths: set[str] = set()
        language_counts: dict[str, int] = {}

        for walked_file in walked_files:
            seen_paths.add(walked_file.relative_path)
            if walked_file.language:
                language_counts[walked_file.language] = language_counts.get(walked_file.language, 0) + 1

            existing = existing_files.get(walked_file.relative_path)
            if existing and not force_full and existing.content_hash == walked_file.content_hash:
                continue  # unchanged -- leave it, and any Phase 5+ data already attached to it, alone

            parent_dir = str(Path(walked_file.relative_path).parent)
            directory_id = directory_ids.get(parent_dir) if parent_dir != "." else None

            if existing:
                existing.content_hash = walked_file.content_hash
                existing.loc = walked_file.loc
                existing.size_bytes = walked_file.size_bytes
                existing.language = walked_file.language
                existing.extension = walked_file.extension
                existing.directory_id = directory_id
                existing.is_test_file = walked_file.is_test_file
                existing.is_generated = walked_file.is_generated
            else:
                self.session.add(
                    File(
                        repository_id=repository_id,
                        directory_id=directory_id,
                        path=walked_file.relative_path,
                        filename=walked_file.filename,
                        extension=walked_file.extension,
                        language=walked_file.language,
                        content_hash=walked_file.content_hash,
                        loc=walked_file.loc,
                        size_bytes=walked_file.size_bytes,
                        is_test_file=walked_file.is_test_file,
                        is_generated=walked_file.is_generated,
                    )
                )

        # Anything that existed before but wasn't seen this walk has been deleted
        # from the repo (or renamed, which we can't distinguish from a delete+add
        # without move-detection -- a reasonable simplification for now).
        for path, row in existing_files.items():
            if path not in seen_paths:
                self.session.delete(row)

        self.session.flush()
        return language_counts

    def _get_repository(self, repository_id: UUID) -> Repository:
        repository = self.session.get(Repository, repository_id)
        if repository is None:
            raise ValueError(f"no repository {repository_id}")
        return repository

    def _set_status(self, repository: Repository, status: IndexingStatus) -> None:
        repository.status = status
        self.session.flush()
