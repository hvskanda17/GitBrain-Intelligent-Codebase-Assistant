"""Sync service used by Celery worker tasks (see workers/tasks/graph.py), same
reasoning as IngestionService/AnalysisService for why it's sync.

Two responsibilities, run in order: resolve every file's imports against the
repository's own files (module_resolver.py -- Python only, see its module
docstring), then project the fully-parsed, fully-resolved repository into the
generic knowledge_nodes/knowledge_edges graph (knowledge_graph_builder.py). Both
pieces of actual logic are pure and independently tested; this class is the thin
data-fetching/persisting wrapper around them, matching the split already
established in AnalysisService.
"""

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models.code_entities import CallGraph, Class, Export, Function, Import, Method
from app.db.models.filesystem import Directory, File
from app.db.models.graph import KnowledgeEdge, KnowledgeNode
from app.db.models.repository import Repository
from app.graph.knowledge_graph_builder import (
    CallEdgeInput,
    ClassInput,
    DirectoryInput,
    FileInput,
    FunctionInput,
    GraphBuildResult,
    ImportEdgeInput,
    MethodInput,
    build_graph,
)
from app.graph.module_resolver import ResolvableFile, build_module_path_index, resolve_import


class KnowledgeGraphService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def resolve_imports(self, repository_id: UUID) -> int:
        files = self.session.scalars(select(File).where(File.repository_id == repository_id)).all()
        module_index = build_module_path_index(
            [ResolvableFile(id=str(f.id), path=f.path, language=f.language) for f in files]
        )
        file_id_lookup = {str(f.id): f.id for f in files}

        imports = self.session.scalars(
            select(Import).join(File, Import.file_id == File.id).where(File.repository_id == repository_id)
        ).all()

        resolved_count = 0
        for imp in imports:
            target_id_str = resolve_import(imp.source_module, imp.imported_symbol, module_index)
            if target_id_str is not None:
                imp.resolved_file_id = file_id_lookup[target_id_str]
                imp.is_external = False
                resolved_count += 1
            else:
                imp.resolved_file_id = None
                imp.is_external = True

        self.session.flush()
        return resolved_count

    def build_graph(self, repository_id: UUID) -> None:
        repository = self.session.get(Repository, repository_id)
        if repository is None:
            raise ValueError(f"no repository {repository_id}")

        directories = self.session.scalars(select(Directory).where(Directory.repository_id == repository_id)).all()
        files = self.session.scalars(select(File).where(File.repository_id == repository_id)).all()
        classes = self.session.scalars(
            select(Class).join(File, Class.file_id == File.id).where(File.repository_id == repository_id)
        ).all()
        methods = self.session.scalars(
            select(Method)
            .join(Class, Method.class_id == Class.id)
            .join(File, Class.file_id == File.id)
            .where(File.repository_id == repository_id)
        ).all()
        functions = self.session.scalars(
            select(Function).join(File, Function.file_id == File.id).where(File.repository_id == repository_id)
        ).all()
        calls = self.session.scalars(select(CallGraph).where(CallGraph.repository_id == repository_id)).all()
        imports = self.session.scalars(
            select(Import).join(File, Import.file_id == File.id).where(File.repository_id == repository_id)
        ).all()

        result = build_graph(
            repository_id=str(repository_id),
            directories=[DirectoryInput(id=str(d.id), name=d.name, parent_id=str(d.parent_id) if d.parent_id else None) for d in directories],
            files=[FileInput(id=str(f.id), filename=f.filename, directory_id=str(f.directory_id) if f.directory_id else None, language=f.language) for f in files],
            classes=[ClassInput(id=str(c.id), file_id=str(c.file_id), name=c.name, parent_class_id=str(c.parent_class_id) if c.parent_class_id else None) for c in classes],
            methods=[MethodInput(id=str(m.id), class_id=str(m.class_id), name=m.name) for m in methods],
            functions=[FunctionInput(id=str(fn.id), file_id=str(fn.file_id), name=fn.name) for fn in functions],
            calls=[
                CallEdgeInput(
                    caller_function_id=str(c.caller_function_id) if c.caller_function_id else None,
                    caller_method_id=str(c.caller_method_id) if c.caller_method_id else None,
                    callee_function_id=str(c.callee_function_id) if c.callee_function_id else None,
                    callee_method_id=str(c.callee_method_id) if c.callee_method_id else None,
                )
                for c in calls
            ],
            imports=[ImportEdgeInput(file_id=str(i.file_id), resolved_file_id=str(i.resolved_file_id) if i.resolved_file_id else None) for i in imports],
        )

        self._persist(repository_id, result)

    def _persist(self, repository_id: UUID, result: GraphBuildResult) -> None:
        # Rebuild is idempotent, same replace-don't-diff reasoning as
        # AnalysisService._persist_result -- the whole graph is cheap enough to
        # regenerate from the (already persisted, already correct) source tables
        # every time, rather than reconciling node-by-node.
        self.session.execute(delete(KnowledgeEdge).where(KnowledgeEdge.repository_id == repository_id))
        self.session.execute(delete(KnowledgeNode).where(KnowledgeNode.repository_id == repository_id))
        self.session.flush()

        node_id_by_key: dict[tuple[str, str], UUID] = {}
        for node_input in result.nodes:
            row = KnowledgeNode(
                repository_id=repository_id,
                node_type=node_input.node_type,
                ref_id=UUID(node_input.ref_id),
                label=node_input.label,
                node_metadata=node_input.metadata,
            )
            self.session.add(row)
            self.session.flush()
            node_id_by_key[(node_input.node_type, node_input.ref_id)] = row.id

        for edge_input in result.edges:
            self.session.add(
                KnowledgeEdge(
                    repository_id=repository_id,
                    source_node_id=node_id_by_key[edge_input.source_key],
                    target_node_id=node_id_by_key[edge_input.target_key],
                    edge_type=edge_input.edge_type,
                    weight=edge_input.weight,
                )
            )

        self.session.flush()
