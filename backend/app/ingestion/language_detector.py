"""Maps file extensions to the languages GitBrain's parsers (Phase 5) will
understand. Deliberately simple -- extension-based mapping is sufficient at the
ingestion stage; Phase 5's tree-sitter parsers are what actually need to know a
file's language precisely, and by then this list can grow without touching
anything else in the pipeline."""

EXTENSION_LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".mts": "typescript",
    ".cts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".c": "c",
    ".h": "c",
    ".php": "php",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".dart": "dart",
}

_EXTENSIONS_BY_LENGTH_DESC = sorted(EXTENSION_LANGUAGE_MAP, key=len, reverse=True)


def detect_language(filename: str) -> str | None:
    for ext in _EXTENSIONS_BY_LENGTH_DESC:
        if filename.endswith(ext):
            return EXTENSION_LANGUAGE_MAP[ext]
    return None


def detect_primary_language(language_counts: dict[str, int]) -> str | None:
    """Simple by-file-count majority. LOC-weighted detection is a reasonable future
    refinement but adds little value until Phase 5 is actually parsing files."""
    if not language_counts:
        return None
    return max(language_counts.items(), key=lambda item: item[1])[0]
