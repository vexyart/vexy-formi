#!/usr/bin/env python3
# this_file: src/vexy_formi/config.py
"""
Simple configuration management for vexy-formi.

Loads configuration from environment variables and optional .vfor.json files.
Keeps it simple - no validation frameworks or complex inheritance.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


class Config:
    """Simple configuration manager."""

    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from all sources."""
        config = {}

        # Start with defaults
        config.update(self._get_defaults())

        # Load from config files (project -> user -> system)
        config.update(self._load_from_files())

        # Override with environment variables
        config.update(self._load_from_env())

        return config

    def _get_defaults(self) -> dict[str, Any]:
        """Get default configuration values."""
        return {
            "max_workers": 4,
            "preferred_js_tool": "esbuild",
            "preferred_css_tool": "biome",
            "preferred_python_tool": "ruff",
            "preferred_html_tool": "html-minifier-terser",
            "create_backup": True,
            "exclude_patterns": [
                ".git/**",
                "node_modules/**",
                ".venv/**",
                "venv/**",
                "__pycache__/**",
                "target/**",
                "dist/**",
                "build/**",
                "*.min.js",
                "*.min.css",
                "*.min.html",
                ".DS_Store",
                "Thumbs.db",
            ],
        }

    def _load_from_files(self) -> dict[str, Any]:
        """Load configuration from .vfor.json files."""
        config = {}

        # Config file locations (in order of precedence)
        config_files = [
            Path.cwd() / ".vfor.json",  # Project level
            Path.home() / ".vfor" / "config.json",  # User level
            Path("/etc/vfor/config.json"),  # System level (lowest priority)
        ]

        # Load each config file (later ones override earlier ones)
        for config_file in reversed(config_files):
            if config_file.exists() and config_file.is_file():
                try:
                    loaded_config = self._load_json_file(config_file)
                    if loaded_config:
                        config.update(loaded_config)
                except Exception:
                    # Just skip invalid config files
                    pass

        return config

    def _load_json_file(self, path: Path) -> dict[str, Any] | None:
        """Load a JSON config file."""
        try:
            with open(path) as f:
                data = json.load(f)

            # Basic validation - must be a dict
            if not isinstance(data, dict):
                return None

            return data

        except (json.JSONDecodeError, OSError):
            return None

    def _load_from_env(self) -> dict[str, Any]:
        """Load configuration from environment variables."""
        config = {}

        # Environment variable mappings
        env_mappings = {
            "VFOR_MAX_WORKERS": ("max_workers", int),
            "VFOR_PREFERRED_JS_TOOL": ("preferred_js_tool", str),
            "VFOR_PREFERRED_CSS_TOOL": ("preferred_css_tool", str),
            "VFOR_PREFERRED_PYTHON_TOOL": ("preferred_python_tool", str),
            "VFOR_PREFERRED_HTML_TOOL": ("preferred_html_tool", str),
            "VFOR_CREATE_BACKUP": ("create_backup", lambda x: x.lower() in ("true", "1", "yes")),
            "VFOR_VERBOSE": ("verbose", lambda x: x.lower() in ("true", "1", "yes")),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                try:
                    config[config_key] = converter(value)
                except (ValueError, TypeError):
                    # Skip invalid values
                    pass

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)

    def get_exclude_patterns(self) -> list[str]:
        """Get exclude patterns from config."""
        return self.config.get("exclude_patterns", [])

    def merge_exclude_patterns(self, additional: list[str] | None = None) -> list[str]:
        """Merge config exclude patterns with additional ones."""
        patterns = self.get_exclude_patterns().copy()
        if additional:
            patterns.extend(additional)
        return patterns


def load_config() -> Config:
    """Load configuration (convenience function)."""
    return Config()


def create_example_config_file(path: Path) -> None:
    """Create an example .vfor.json config file."""
    example_config = {
        "preferred_js_tool": "esbuild",
        "preferred_css_tool": "biome",
        "preferred_python_tool": "ruff",
        "preferred_html_tool": "html-minifier-terser",
        "max_workers": 4,
        "create_backup": True,
        "exclude_patterns": ["*.min.*", "node_modules/**", "dist/**", "build/**", ".git/**"],
    }

    with open(path, "w") as f:
        json.dump(example_config, f, indent=4)


# For backward compatibility - these were referenced in tools.py
def get_preferred_tool(tool_type: str, config: Config | None = None) -> str:
    """Get preferred tool for a given type."""
    if config is None:
        config = load_config()

    key_mapping = {
        "js": "preferred_js_tool",
        "css": "preferred_css_tool",
        "python": "preferred_python_tool",
        "html": "preferred_html_tool",
    }

    key = key_mapping.get(tool_type, f"preferred_{tool_type}_tool")
    return config.get(key, "auto")
