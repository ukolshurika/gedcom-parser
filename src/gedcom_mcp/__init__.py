"""
GEDCOM MCP - A library for parsing and querying GEDCOM genealogy files.

This package provides:
- FastAPI server for REST API access
- MCP (Model Context Protocol) server for AI integrations
- GEDCOM parsing and analysis utilities
"""

# Lazy imports to avoid circular dependencies and missing module errors
__all__ = [
    "app",
    "GedcomContext",
    "get_gedcom_context",
]


def __getattr__(name):
    """Lazy import of package components."""
    if name == "app":
        from .app import app
        return app
    elif name == "GedcomContext":
        from .gedcom_context import GedcomContext
        return GedcomContext
    elif name == "get_gedcom_context":
        from .gedcom_context import get_gedcom_context
        return get_gedcom_context
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
