"""Python entity extractor.

Confidence note, worth reading before trusting this against real code: the core
shapes used here -- `function_definition`/`class_definition` nodes, `name`/`body`/
`parameters`/`superclasses` fields, `call` with `function`/`arguments` fields -- are
confirmed directly against the official py-tree-sitter README's worked Python
example (github.com/tree-sitter/py-tree-sitter), not just recalled. Docstring
detection, decorator/staticmethod handling, and specifically the `async def`
check (`node.children[0]` literally being the token "async") are written from
well-established tree-sitter-python usage patterns but have NOT been executed
against a real parser in this environment -- no network here to install
tree-sitter. Run tests/unit/test_python_parser_smoke.py locally after
`pip install tree-sitter tree-sitter-language-pack` before trusting this in
production; it's written to fail loudly and specifically if any of these
assumptions are wrong, rather than silently producing empty results.

Method call sites are attributed to a qualified caller name ("ClassName.method_name"),
matching the qualified_name convention app/services/analysis_service.py uses when
building the KnownCallable list for app/analysis/call_graph_resolver.py -- a parser
for another language should follow the same convention so call resolution isn't
language-dependent.
"""

from typing import Any

from app.parsers.base_parser import BaseLanguageParser
from app.parsers.entities import (
    CallSite,
    ClassEntity,
    FunctionEntity,
    ImportEntity,
    MethodEntity,
    ParameterInfo,
    ParseResult,
)
from app.parsers.tree_sitter_manager import get_parser


class PythonParser(BaseLanguageParser):
    language = "python"

    def parse_source(self, source: str) -> Any:
        return get_parser(self.language).parse(bytes(source, "utf8"))

    def extract(self, tree: Any, source: str) -> ParseResult:
        result = ParseResult()
        src_bytes = bytes(source, "utf8")

        for child in tree.root_node.children:
            self._extract_top_level(child, src_bytes, result)

        return result

    # ---- top-level dispatch -------------------------------------------------

    def _extract_top_level(self, node: Any, src_bytes: bytes, result: ParseResult) -> None:
        if node.type == "import_statement":
            self._extract_import_statement(node, src_bytes, result)
        elif node.type == "import_from_statement":
            self._extract_import_from_statement(node, src_bytes, result)
        elif node.type == "function_definition":
            self._extract_function(node, src_bytes, result)
        elif node.type == "class_definition":
            self._extract_class(node, src_bytes, result)
        elif node.type == "decorated_definition":
            definition = node.child_by_field_name("definition")
            if definition is not None:
                self._extract_top_level(definition, src_bytes, result)

    # ---- imports --------------------------------------------------------------

    def _extract_import_statement(self, node: Any, src_bytes: bytes, result: ParseResult) -> None:
        for child in node.children:
            if child.type == "dotted_name":
                module = self._text(child, src_bytes)
                result.imports.append(
                    ImportEntity(
                        imported_symbol=module,
                        source_module=module,
                        alias=None,
                        line_number=node.start_point[0] + 1,
                    )
                )
            elif child.type == "aliased_import":
                self._append_aliased_import(child, src_bytes, result, module="")

    def _extract_import_from_statement(self, node: Any, src_bytes: bytes, result: ParseResult) -> None:
        module_node = node.child_by_field_name("module_name")
        module = self._text(module_node, src_bytes) if module_node is not None else ""
        for child in node.children:
            if child.type == "dotted_name" and child is not module_node:
                result.imports.append(
                    ImportEntity(
                        imported_symbol=self._text(child, src_bytes),
                        source_module=module,
                        alias=None,
                        line_number=node.start_point[0] + 1,
                    )
                )
            elif child.type == "aliased_import":
                self._append_aliased_import(child, src_bytes, result, module=module)

    def _append_aliased_import(self, node: Any, src_bytes: bytes, result: ParseResult, *, module: str) -> None:
        name_node = node.child_by_field_name("name")
        alias_node = node.child_by_field_name("alias")
        if name_node is None:
            return
        symbol = self._text(name_node, src_bytes)
        result.imports.append(
            ImportEntity(
                imported_symbol=symbol,
                source_module=module or symbol,
                alias=self._text(alias_node, src_bytes) if alias_node is not None else None,
                line_number=node.start_point[0] + 1,
            )
        )

    # ---- functions & classes ---------------------------------------------------

    def _extract_function(self, node: Any, src_bytes: bytes, result: ParseResult) -> None:
        fn = self._build_function(node, src_bytes)
        result.functions.append(fn)
        result.calls.extend(self._find_calls(node.child_by_field_name("body"), src_bytes, fn.name))

    def _extract_class(self, node: Any, src_bytes: bytes, result: ParseResult) -> None:
        name_node = node.child_by_field_name("name")
        body_node = node.child_by_field_name("body")
        superclasses_node = node.child_by_field_name("superclasses")
        name = self._text(name_node, src_bytes) if name_node is not None else "<anonymous>"

        parent_name = None
        if superclasses_node is not None:
            bases = [c for c in superclasses_node.children if c.type == "identifier"]
            if bases:
                parent_name = self._text(bases[0], src_bytes)

        methods: list[MethodEntity] = []
        if body_node is not None:
            for child in body_node.children:
                target, is_static = child, False
                if child.type == "decorated_definition":
                    target = child.child_by_field_name("definition")
                    decorator_text = "".join(
                        self._text(d, src_bytes) for d in child.children if d.type == "decorator"
                    )
                    is_static = "staticmethod" in decorator_text or "classmethod" in decorator_text
                if target is not None and target.type == "function_definition":
                    method = self._build_method(target, src_bytes, is_static=is_static)
                    methods.append(method)
                    qualified_caller = f"{name}.{method.name}"
                    result.calls.extend(
                        self._find_calls(target.child_by_field_name("body"), src_bytes, qualified_caller)
                    )

        result.classes.append(
            ClassEntity(
                name=name,
                qualified_name=name,
                docstring=self._docstring(body_node, src_bytes),
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1,
                parent_class_name=parent_name,
                is_abstract=False,  # real ABC detection needs cross-referencing the `abc` import -- later pass
                methods=methods,
            )
        )

    def _build_function(self, node: Any, src_bytes: bytes) -> FunctionEntity:
        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        return_type_node = node.child_by_field_name("return_type")
        name = self._text(name_node, src_bytes) if name_node is not None else "<anonymous>"
        params = self._parameters(params_node, src_bytes)
        return FunctionEntity(
            name=name,
            qualified_name=name,
            signature=f"def {name}({', '.join(p.name for p in params)})",
            return_type=self._text(return_type_node, src_bytes) if return_type_node is not None else None,
            parameters=params,
            docstring=self._docstring(node.child_by_field_name("body"), src_bytes),
            is_async=self._is_async(node, src_bytes),
            is_exported=not name.startswith("_"),
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
        )

    def _build_method(self, node: Any, src_bytes: bytes, *, is_static: bool) -> MethodEntity:
        name_node = node.child_by_field_name("name")
        params_node = node.child_by_field_name("parameters")
        return_type_node = node.child_by_field_name("return_type")
        name = self._text(name_node, src_bytes) if name_node is not None else "<anonymous>"
        params = self._parameters(params_node, src_bytes)
        if name.startswith("__") and not name.endswith("__"):
            visibility = "private"
        elif name.startswith("_"):
            visibility = "protected"
        else:
            visibility = "public"
        return MethodEntity(
            name=name,
            signature=f"def {name}({', '.join(p.name for p in params)})",
            return_type=self._text(return_type_node, src_bytes) if return_type_node is not None else None,
            visibility=visibility,
            is_static=is_static,
            is_async=self._is_async(node, src_bytes),
            docstring=self._docstring(node.child_by_field_name("body"), src_bytes),
            start_line=node.start_point[0] + 1,
            end_line=node.end_point[0] + 1,
        )

    # ---- calls ------------------------------------------------------------

    def _find_calls(self, node: Any, src_bytes: bytes, caller_name: str) -> list[CallSite]:
        """Recurses through a function/method body collecting every `call` node. A
        nested `def` inside the body still has its calls walked (correctness), but
        they're attributed to the OUTER caller_name rather than getting their own
        identity, since nested/local functions aren't currently registered as their
        own FunctionEntity -- a reasonable, documented gap rather than a silent
        miss: those calls still show up in the graph, just one level less precise
        than they could be."""
        if node is None:
            return []
        calls: list[CallSite] = []
        if node.type == "call":
            function_node = node.child_by_field_name("function")
            if function_node is not None:
                if function_node.type == "attribute":
                    attr_node = function_node.child_by_field_name("attribute")
                    callee_name = (
                        self._text(attr_node, src_bytes) if attr_node is not None else self._text(function_node, src_bytes)
                    )
                else:
                    callee_name = self._text(function_node, src_bytes)
                calls.append(
                    CallSite(caller_name=caller_name, callee_name=callee_name, line_number=node.start_point[0] + 1)
                )
        for child in node.children:
            calls.extend(self._find_calls(child, src_bytes, caller_name))
        return calls

    # ---- small helpers ------------------------------------------------------

    def _text(self, node: Any, src_bytes: bytes) -> str:
        return src_bytes[node.start_byte : node.end_byte].decode("utf8")

    def _docstring(self, body_node: Any, src_bytes: bytes) -> str | None:
        if body_node is None or body_node.child_count == 0:
            return None
        first = body_node.children[0]
        if first.type == "expression_statement" and first.child_count and first.children[0].type == "string":
            return self._text(first.children[0], src_bytes).strip("\"'").strip()
        return None

    def _is_async(self, node: Any, src_bytes: bytes) -> bool:
        # LOWER CONFIDENCE than the rest of this file -- see the module docstring.
        return bool(node.children) and self._text(node.children[0], src_bytes) == "async"

    def _parameters(self, params_node: Any, src_bytes: bytes) -> list[ParameterInfo]:
        if params_node is None:
            return []
        params: list[ParameterInfo] = []
        for child in params_node.children:
            if child.type == "identifier":
                params.append(ParameterInfo(name=self._text(child, src_bytes)))
            elif child.type in ("typed_parameter", "default_parameter", "typed_default_parameter"):
                name_node = child.child_by_field_name("name")
                if name_node is None and child.children and child.children[0].type == "identifier":
                    name_node = child.children[0]
                type_node = child.child_by_field_name("type")
                value_node = child.child_by_field_name("value")
                if name_node is not None:
                    params.append(
                        ParameterInfo(
                            name=self._text(name_node, src_bytes),
                            type_annotation=self._text(type_node, src_bytes) if type_node is not None else None,
                            default=self._text(value_node, src_bytes) if value_node is not None else None,
                        )
                    )
        return params
