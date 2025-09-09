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

from .core import minify_files, format_files, FileProcessor
from .tools import get_available_tools, detect_file_type, ToolManager
from .files import find_files, validate_file, FileHandler

__version__ = "1.0.0"
__all__ = [
    "minify_files", 
    "format_files", 
    "FileProcessor",
    "ToolManager", 
    "FileHandler",
    "get_available_tools", 
    "detect_file_type", 
    "find_files", 
    "validate_file",
    "minify",
    "format"
]

# Simple API for programmatic use
def minify(path, **kwargs):
    """Minify files at the given path."""
    return minify_files(path, **kwargs)

def format(path, **kwargs):
    """Format files at the given path."""  
    return format_files(path, **kwargs)