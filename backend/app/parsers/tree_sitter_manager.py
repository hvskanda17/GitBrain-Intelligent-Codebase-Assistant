"""Loads and caches tree-sitter parsers across every language GitBrain targets, via
tree-sitter-language-pack -- one dependency covering all 14 languages from the
original spec, rather than a separate tree-sitter-<language> package per language
(each of which would need its own pinned version and its own ABI-compatibility check
against the core tree-sitter package).
"""

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tree_sitter import Parser


class UnsupportedLanguageError(Exception):
    pass


# GitBrain's own language names (matching app.ingestion.language_detector) mapped to
# tree-sitter-language-pack's grammar names, where they differ from ours.
LANGUAGE_PACK_NAMES: dict[str, str] = {
    "python": "python",
    "java": "java",
    "javascript": "javascript",
    "typescript": "typescript",
    "go": "go",
    "rust": "rust",
    "csharp": "c_sharp",
    "cpp": "cpp",
    "c": "c",
    "php": "php",
    "ruby": "ruby",
    "kotlin": "kotlin",
    "swift": "swift",
    "dart": "dart",
}


@lru_cache(maxsize=None)
def get_parser(language: str) -> "Parser":
    if language not in LANGUAGE_PACK_NAMES:
        raise UnsupportedLanguageError(f"no tree-sitter grammar mapped for '{language}'")

    from tree_sitter_language_pack import get_parser as _get_parser

    try:
        return _get_parser(LANGUAGE_PACK_NAMES[language])
    except Exception as exc:
        raise UnsupportedLanguageError(
            f"tree-sitter-language-pack has no grammar for '{language}'"
        ) from exc
