#!/usr/bin/env python3
# this_file: src/vexy_formi/__init__.py
"""
VexyFormi - Fast code formatting and minification tool.

A simple, efficient tool for minifying and formatting code using the fastest
available tools (esbuild, swc, biome, ruff, etc.).

Simple usage:
    import vexy_formi

    # Minify files
    result = vexy_formi.minify('src/')

    # Format files
    result = vexy_formi.format('src/')

    # Check available tools
    tools = vexy_formi.get_available_tools()
"""

from .core import FileProcessor, format_files, minify_files
from .files import FileHandler, find_files, validate_file
from .tools import ToolManager, detect_file_type, get_available_tools

__version__ = "1.0.0"
__all__ = [
    "FileHandler",
    "FileProcessor",
    "ToolManager",
    "detect_file_type",
    "find_files",
    "format",
    "format_files",
    "get_available_tools",
    "minify",
    "minify_files",
    "validate_file",
]


# Simple API for programmatic use
def minify(path, **kwargs):
    """Minify files at the given path."""
    return minify_files(path, **kwargs)


def format(path, **kwargs):
    """Format files at the given path."""
    return format_files(path, **kwargs)
