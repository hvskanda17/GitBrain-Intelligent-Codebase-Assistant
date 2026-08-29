from app.parsers.base_parser import BaseLanguageParser
from app.parsers.extractors.python_parser import PythonParser


class NoExtractorForLanguageError(Exception):
    pass


EXTRACTORS: dict[str, type[BaseLanguageParser]] = {
    "python": PythonParser,
    # Phase 5 ships one language end-to-end. Every other language in
    # app.parsers.tree_sitter_manager.LANGUAGE_PACK_NAMES already has a grammar
    # available via tree-sitter-language-pack -- adding support for one is writing
    # a BaseLanguageParser subclass following python_parser.py's pattern (and its
    # confidence-level notes on what to check against a real parser) and
    # registering it here. Nothing else in the pipeline changes.
}


def get_extractor(language: str | None) -> BaseLanguageParser:
    if language is None or language not in EXTRACTORS:
        raise NoExtractorForLanguageError(language)
    return EXTRACTORS[language]()
