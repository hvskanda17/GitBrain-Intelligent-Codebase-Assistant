"""The contract every language extractor implements. Everything downstream --
app/services/analysis_service.py, app/analysis/*, the DB writes -- only ever talks
to this interface, never to a specific language's tree-sitter node types. Adding a
language means writing one class that satisfies this and registering it with
TreeSitterManager; nothing else changes.
"""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from app.parsers.entities import ParseResult


class BaseLanguageParser(ABC):
    language: ClassVar[str]

    @abstractmethod
    def parse_source(self, source: str) -> Any:
        """Returns a tree-sitter Tree (or equivalent). Kept separate from extract()
        so a caller that needs the raw tree for something else (a future syntax
        highlighter, say) doesn't have to extract entities it doesn't need."""

    @abstractmethod
    def extract(self, tree: Any, source: str) -> ParseResult:
        """Walks `tree` once and returns everything this file yields. A single
        combined pass rather than four separate extract_functions/extract_classes/...
        calls -- most of what a real query needs (which class a method belongs to,
        which function a call site is inside) falls out naturally from one
        traversal and has to be reconstructed expensively if each entity type is
        extracted independently."""
