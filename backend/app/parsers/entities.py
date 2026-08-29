"""Every language extractor returns these same shapes regardless of the underlying
grammar -- this is what lets app/services/analysis_service.py and everything in
app/analysis/ stay language-agnostic. A new language extractor is "done" when it can
produce these from its own tree-sitter tree; nothing downstream needs to change."""

from dataclasses import dataclass, field


@dataclass
class ParameterInfo:
    name: str
    type_annotation: str | None = None
    default: str | None = None


@dataclass
class FunctionEntity:
    name: str
    qualified_name: str | None
    signature: str
    return_type: str | None
    parameters: list[ParameterInfo]
    docstring: str | None
    is_async: bool
    is_exported: bool
    start_line: int
    end_line: int
    complexity_score: int | None = None


@dataclass
class MethodEntity:
    name: str
    signature: str
    return_type: str | None
    visibility: str  # "public" | "private" | "protected"
    is_static: bool
    is_async: bool
    docstring: str | None
    start_line: int
    end_line: int


@dataclass
class ClassEntity:
    name: str
    qualified_name: str | None
    docstring: str | None
    start_line: int
    end_line: int
    parent_class_name: str | None  # resolved to a parent_class_id by name, once persisted
    is_abstract: bool
    methods: list[MethodEntity] = field(default_factory=list)


@dataclass
class ImportEntity:
    imported_symbol: str
    source_module: str
    alias: str | None
    line_number: int


@dataclass
class ExportEntity:
    symbol_name: str
    symbol_type: str  # "function" | "class" | "const" | "type"
    line_number: int


@dataclass
class CallSite:
    """caller_name is the enclosing function/method's name, or None for a call made
    at module level (outside any function) -- call_graph_resolver.py drops those,
    since call_graph rows require a caller."""

    caller_name: str | None
    callee_name: str
    line_number: int


@dataclass
class ParseResult:
    functions: list[FunctionEntity] = field(default_factory=list)
    classes: list[ClassEntity] = field(default_factory=list)
    imports: list[ImportEntity] = field(default_factory=list)
    exports: list[ExportEntity] = field(default_factory=list)
    calls: list[CallSite] = field(default_factory=list)
