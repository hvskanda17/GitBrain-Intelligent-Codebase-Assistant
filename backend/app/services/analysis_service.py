"""Sync service used by Celery worker tasks (see workers/tasks/parsing.py), same
reasoning as IngestionService for why it's sync rather than sharing the API's async
engine.

Two-pass call resolution, matching the design in app/analysis/call_graph_resolver.py:
parse_repository_files() resolves same-file calls immediately, since the caller is
always known (it's the function/method just parsed) and same-file callees are
already in hand. build_repository_call_graph() makes a second pass afterward,
re-attempting resolution for whatever's left unresolved -- calls whose callee lives
in a different file -- now that every file in the repository has been parsed and a
full callable index can be built.
"""

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.analysis.call_graph_resolver import CallableIndex, KnownCallable
from app.core.logging import get_logger
from app.db.models.code_entities import CallGraph, Class, Export, Function, Import, Method
from app.db.models.filesystem import File
from app.db.models.repository import IndexingStatus, Repository
from app.parsers.entities import ParseResult
from app.parsers.registry import NoExtractorForLanguageError, get_extractor

logger = get_logger(__name__)


class AnalysisService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def parse_repository_files(self, repository_id: UUID) -> None:
        repository = self._get_repository(repository_id)
        repository.status = IndexingStatus.ANALYZING
        self.session.flush()

        files = self.session.scalars(select(File).where(File.repository_id == repository_id)).all()
        for file in files:
            self._parse_one_file(repository, file)

        self.session.flush()

    def build_repository_call_graph(self, repository_id: UUID) -> None:
        functions = self.session.scalars(
            select(Function).join(File, Function.file_id == File.id).where(File.repository_id == repository_id)
        ).all()
        methods_with_class = self.session.execute(
            select(Method, Class)
            .join(Class, Method.class_id == Class.id)
            .join(File, Class.file_id == File.id)
            .where(File.repository_id == repository_id)
        ).all()

        callables = [KnownCallable(id=str(f.id), name=f.name, qualified_name=f.qualified_name) for f in functions]
        callables += [
            KnownCallable(id=str(m.id), name=m.name, qualified_name=f"{c.name}.{m.name}")
            for m, c in methods_with_class
        ]
        index = CallableIndex(callables)

        unresolved = self.session.scalars(
            select(CallGraph).where(
                CallGraph.repository_id == repository_id,
                CallGraph.callee_function_id.is_(None),
                CallGraph.callee_method_id.is_(None),
            )
        ).all()

        resolved_count = 0
        for edge in unresolved:
            if edge.callee_raw_name is None:
                continue
            match = index.match(edge.callee_raw_name)
            if match is None:
                continue
            # Same convention as _persist_calls: a method's qualified_name always
            # contains "Class.method", a function's is just its bare name.
            if "." in (match.qualified_name or ""):
                edge.callee_method_id = UUID(match.id)
            else:
                edge.callee_function_id = UUID(match.id)
            resolved_count += 1

        logger.info(
            "analysis.call_graph.cross_file_resolved repository_id=%s resolved=%d of %d",
            repository_id,
            resolved_count,
            len(unresolved),
        )
        self.session.flush()

    # ---- per-file parsing ----------------------------------------------------

    def _parse_one_file(self, repository: Repository, file: File) -> None:
        if file.language is None:
            return  # no recognized language (README, config, etc.) -- nothing to parse

        try:
            extractor = get_extractor(file.language)
        except NoExtractorForLanguageError:
            return  # ingestion recognizes the language; Phase 5 doesn't have a parser for it yet

        if not repository.local_path:
            return

        absolute_path = Path(repository.local_path) / file.path
        try:
            source = absolute_path.read_text(errors="replace")
        except OSError as exc:
            logger.warning("analysis.read_failed file_id=%s error=%s", file.id, exc)
            return

        try:
            tree = extractor.parse_source(source)
            result = extractor.extract(tree, source)
        except Exception as exc:
            # A parser degrading gracefully on one malformed/unusual file should
            # never take down the whole repository's analysis run.
            logger.warning("analysis.parse_failed file_id=%s language=%s error=%s", file.id, file.language, exc)
            return

        self._persist_result(file, result)
        file.last_parsed_at = datetime.now(timezone.utc)
        self.session.flush()

    def _persist_result(self, file: File, result: ParseResult) -> None:
        # Replace, don't diff -- simpler and safer than reconciling function-by-
        # function, and re-parsing one file is cheap enough to fully redo. Deleting
        # classes cascades to their methods (ON DELETE CASCADE in the schema);
        # deleting functions/imports/exports/call_graph rows referencing this file's
        # functions/methods needs the same cascade, which the FKs already provide.
        self.session.execute(delete(Function).where(Function.file_id == file.id))
        self.session.execute(delete(Class).where(Class.file_id == file.id))
        self.session.execute(delete(Import).where(Import.file_id == file.id))
        self.session.execute(delete(Export).where(Export.file_id == file.id))
        self.session.flush()

        # name -> (id, is_method) for same-file call resolution below
        same_file_callables: dict[str, KnownCallable] = {}

        for fn in result.functions:
            row = Function(
                file_id=file.id,
                name=fn.name,
                qualified_name=fn.qualified_name,
                signature=fn.signature,
                return_type=fn.return_type,
                parameters=[asdict(p) for p in fn.parameters],
                docstring=fn.docstring,
                is_async=fn.is_async,
                is_exported=fn.is_exported,
                start_line=fn.start_line,
                end_line=fn.end_line,
            )
            self.session.add(row)
            self.session.flush()
            same_file_callables[fn.name] = KnownCallable(id=str(row.id), name=fn.name, qualified_name=fn.name)

        for cls in result.classes:
            class_row = Class(
                file_id=file.id,
                name=cls.name,
                qualified_name=cls.qualified_name,
                docstring=cls.docstring,
                start_line=cls.start_line,
                end_line=cls.end_line,
                is_abstract=False,  # real ABC detection needs cross-referencing the language's abc convention -- later pass
            )
            self.session.add(class_row)
            self.session.flush()

            for method in cls.methods:
                method_row = Method(
                    class_id=class_row.id,
                    name=method.name,
                    signature=method.signature,
                    return_type=method.return_type,
                    visibility=method.visibility,
                    is_static=method.is_static,
                    is_async=method.is_async,
                    docstring=method.docstring,
                    start_line=method.start_line,
                    end_line=method.end_line,
                )
                self.session.add(method_row)
                self.session.flush()
                qualified = f"{cls.name}.{method.name}"
                # Keyed by qualified name ONLY -- caller lookups use this exact key
                # (call.caller_name is always "Class.method" for a method, never the
                # bare name), so there's no ambiguity here. The CALLEE side, where
                # bare-name ambiguity between two same-named methods genuinely
                # matters, is handled entirely inside CallableIndex in
                # _persist_calls -- this dict must hold exactly one entry per
                # callable, not a second bare-name alias for it, or CallableIndex
                # sees duplicate registrations and wrongly calls every same-named
                # method "ambiguous" even when only one actually exists.
                same_file_callables[qualified] = KnownCallable(
                    id=str(method_row.id), name=method.name, qualified_name=qualified
                )

        for imp in result.imports:
            self.session.add(
                Import(
                    file_id=file.id,
                    imported_symbol=imp.imported_symbol,
                    source_module=imp.source_module,
                    alias=imp.alias,
                    line_number=imp.line_number,
                    # Matching an import to an actual file in the repo (vs. an
                    # external package) needs per-language module-path resolution
                    # (Python's dotted paths, JS/TS relative and tsconfig-aliased
                    # paths) -- Phase 6's job, alongside the rest of knowledge-graph
                    # construction. True until then, since most imports in most
                    # files are external anyway.
                    is_external=True,
                )
            )

        self._persist_calls(file, result, same_file_callables)
        self.session.flush()

    def _persist_calls(self, file: File, result: ParseResult, same_file_callables: dict[str, KnownCallable]) -> None:
        # One real entry per callable (see the comment where same_file_callables is
        # built) -- CallableIndex does its own bare-name-ambiguity bookkeeping over
        # exactly that list, so a genuinely unambiguous same-named method resolves,
        # and a genuinely ambiguous one (two classes in this file both define
        # `save`) correctly does not.
        index = CallableIndex(list(same_file_callables.values()))
        caller_ids_by_name = {name: c.id for name, c in same_file_callables.items()}

        for call in result.calls:
            caller_id = caller_ids_by_name.get(call.caller_name) if call.caller_name else None
            if caller_id is None:
                continue  # a call made at module level (outside any function) -- call_graph needs a caller

            match = index.match(call.callee_name)
            is_caller_method = "." in (call.caller_name or "")
            row = CallGraph(
                repository_id=file.repository_id,
                call_line=call.line_number,
                callee_raw_name=None if match else call.callee_name,
            )
            if is_caller_method:
                row.caller_method_id = UUID(caller_id)
            else:
                row.caller_function_id = UUID(caller_id)
            if match:
                # A method's qualified_name is always "Class.method" (set that way
                # above); a function's is just its bare name, with no dot -- cheaper
                # and just as reliable as a second id->type lookup table.
                if "." in (match.qualified_name or ""):
                    row.callee_method_id = UUID(match.id)
                else:
                    row.callee_function_id = UUID(match.id)
            self.session.add(row)

    def _get_repository(self, repository_id: UUID) -> Repository:
        repository = self.session.get(Repository, repository_id)
        if repository is None:
            raise ValueError(f"no repository {repository_id}")
        return repository
