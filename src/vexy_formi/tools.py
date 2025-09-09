#!/usr/bin/env python3
# this_file: src/vexy_formi/tools.py
"""
Fast tool detection and execution for vexy-formi.

Simplified version extracted from unimini, focusing on speed and reliability
while removing enterprise bloat. Prioritizes Rust/Go tools for maximum performance.
"""

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import Config


class ToolManager:
    """Manages tool detection and execution with focus on speed."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self._tool_cache = {}
        self._cache_dir = Path.home() / ".cache" / "vfor"
        self._cache_file = self._cache_dir / "tool_cache.json"
        self._cache_ttl = 3600  # 1 hour cache TTL

        # Create cache directory if it doesn't exist
        self._cache_dir.mkdir(parents=True, exist_ok=True)

        # Tool categories for lazy loading
        self._essential_tools = {
            # Most commonly used tools - detect immediately
            "ruff",
            "biome",
            "prettier",
            "black",
            "esbuild",
        }
        self._frequently_used_tools = {
            # Common tools - detect on demand
            "swc",
            "terser",
            "lightningcss",
            "dprint",
        }
        self._rarely_used_tools = {
            # Less common tools - lazy load only when needed
            "minify",
            "taplo",
            "jq",
            "yq",
            "html-minifier-terser",
        }

        # Load cached tools or detect essential ones
        self._initialize_tools()
        self._setup_tool_commands()

    def _initialize_tools(self):
        """Initialize tools with lazy loading - only detect essential tools immediately."""
        # Try loading from cache first
        cached_tools = self._load_cache()
        if cached_tools is not None:
            self._tool_cache = cached_tools
            return

        # Cache miss - only detect essential tools immediately
        essential_cache = {}
        for tool in self._essential_tools:
            essential_cache[tool] = self._is_tool_available(tool)

        self._tool_cache = essential_cache

        # Note: Other tools will be detected lazily when first requested

    def _ensure_tool_detected(self, tool: str) -> bool:
        """Ensure a specific tool is detected, using lazy loading if necessary."""
        if tool in self._tool_cache:
            return self._tool_cache[tool]

        # Tool not in cache - detect it now
        is_available = self._is_tool_available(tool)
        self._tool_cache[tool] = is_available

        # Update persistent cache with new tool
        self._update_cache_with_tool(tool, is_available)

        return is_available

    def _update_cache_with_tool(self, tool: str, is_available: bool):
        """Add a single tool to the persistent cache."""
        try:
            # Load existing cache
            cache_data = {}
            if self._cache_file.exists():
                with open(self._cache_file) as f:
                    cache_data = json.load(f)

            # Update with new tool
            if "tools" not in cache_data:
                cache_data["tools"] = {}
            cache_data["tools"][tool] = is_available
            cache_data["timestamp"] = time.time()
            cache_data["env_hash"] = self._get_environment_hash()

            # Atomic write
            temp_file = self._cache_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(cache_data, f, indent=2)
            temp_file.rename(self._cache_file)
        except Exception:
            # If cache update fails, continue without caching
            pass

    def _get_environment_hash(self) -> str:
        """Generate hash of current environment for cache invalidation."""
        # Include PATH and other relevant environment variables
        env_data = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
            "NODE_PATH": os.environ.get("NODE_PATH", ""),
        }
        env_string = json.dumps(env_data, sort_keys=True)
        return hashlib.md5(env_string.encode()).hexdigest()

    def _load_cache(self) -> dict | None:
        """Load tool availability cache from disk."""
        try:
            if not self._cache_file.exists():
                return None

            with open(self._cache_file) as f:
                cache_data = json.load(f)

            # Check if cache is still valid
            current_time = time.time()
            current_env_hash = self._get_environment_hash()

            # Validate cache freshness and environment
            if (
                cache_data.get("timestamp", 0) + self._cache_ttl < current_time
                or cache_data.get("env_hash") != current_env_hash
            ):
                return None

            return cache_data.get("tools", {})
        except Exception:
            # If cache loading fails, just return None to trigger fresh detection
            return None

    def _save_cache(self, tools: dict[str, bool]):
        """Save tool availability cache to disk."""
        try:
            cache_data = {
                "timestamp": time.time(),
                "env_hash": self._get_environment_hash(),
                "tools": tools,
            }

            # Atomic write to avoid corruption
            temp_file = self._cache_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(cache_data, f, indent=2)

            # Atomic move
            temp_file.rename(self._cache_file)
        except Exception:
            # If cache saving fails, continue without caching
            pass

    def _detect_tools(self):
        """Detect available tools quickly with caching for performance."""
        # Try loading from cache first
        cached_tools = self._load_cache()
        if cached_tools is not None:
            self._tool_cache = cached_tools
            return

        # Cache miss - detect tools with subprocess calls
        tools_to_check = [
            # Fast minifiers (Rust/Go)
            "esbuild",
            "swc",
            "biome",
            "ruff",
            "lightningcss",
            "minify",
            "taplo",
            "dprint",
            # Standard tools
            "terser",
            "prettier",
            "black",
            "jq",
            "yq",
            "html-minifier-terser",
        ]

        fresh_cache = {}
        for tool in tools_to_check:
            fresh_cache[tool] = self._is_tool_available(tool)

        self._tool_cache = fresh_cache

        # Save to cache for future use
        self._save_cache(fresh_cache)

    def _is_tool_available(self, tool: str) -> bool:
        """Quick tool availability check."""
        try:
            # Try which/where first (fastest)
            cmd = "where" if os.name == "nt" else "which"
            result = subprocess.run([cmd, tool], check=False, capture_output=True, timeout=2)
            if result.returncode == 0:
                return True

            # Fallback to version check
            result = subprocess.run([tool, "--version"], check=False, capture_output=True, timeout=3)
            return result.returncode == 0
        except Exception:
            return False

    def _setup_tool_commands(self):
        """Set up command templates for each tool and file type."""

        # Tool command templates
        self.minify_commands = {
            # JavaScript/TypeScript (priority: esbuild → swc → terser)
            ".js": [
                ("esbuild", ["esbuild", "{input}", "--minify", "--outfile={output}"]),
                ("swc", ["swc", "{input}", "--minify", "-o", "{output}"]),
                ("terser", ["terser", "{input}", "-c", "-m", "-o", "{output}"]),
            ],
            ".ts": [
                ("esbuild", ["esbuild", "{input}", "--minify", "--outfile={output}"]),
                ("swc", ["swc", "{input}", "--minify", "-o", "{output}"]),
            ],
            ".jsx": [
                ("esbuild", ["esbuild", "{input}", "--minify", "--outfile={output}"]),
                ("swc", ["swc", "{input}", "--minify", "-o", "{output}"]),
            ],
            ".tsx": [
                ("esbuild", ["esbuild", "{input}", "--minify", "--outfile={output}"]),
                ("swc", ["swc", "{input}", "--minify", "-o", "{output}"]),
            ],
            # CSS (priority: biome → lightningcss → built-in)
            ".css": [
                ("lightningcss", ["lightningcss", "{input}", "-o", "{output}", "--minify"]),
                ("biome", ["biome", "format", "{input}", "--write"]),  # Format as minify
            ],
            ".scss": [
                ("lightningcss", ["lightningcss", "{input}", "-o", "{output}", "--minify"]),
            ],
            # HTML (priority: html-minifier-terser)
            ".html": [
                (
                    "html-minifier-terser",
                    [
                        "html-minifier-terser",
                        "{input}",
                        "-o",
                        "{output}",
                        "--collapse-whitespace",
                        "--remove-comments",
                    ],
                ),
            ],
            ".htm": [
                (
                    "html-minifier-terser",
                    [
                        "html-minifier-terser",
                        "{input}",
                        "-o",
                        "{output}",
                        "--collapse-whitespace",
                        "--remove-comments",
                    ],
                ),
            ],
            # JSON (priority: jq → built-in minifier)
            ".json": [
                (
                    "jq",
                    ["jq", "-c", ".", "{input}"],
                ),  # Compact JSON - will handle output in execute_command
            ],
            ".jsonc": [
                ("biome", ["biome", "format", "{input}", "--write"]),
            ],
        }

        self.format_commands = {
            # Python (priority: ruff → black)
            ".py": [
                ("ruff", ["ruff", "format", "{input}"]),
                ("black", ["black", "{input}"]),
            ],
            # JavaScript/TypeScript (priority: biome → prettier → dprint)
            ".js": [
                ("biome", ["biome", "format", "--write", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
                ("dprint", ["dprint", "fmt", "{input}"]),
            ],
            ".ts": [
                ("biome", ["biome", "format", "--write", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
                ("dprint", ["dprint", "fmt", "{input}"]),
            ],
            ".jsx": [
                ("biome", ["biome", "format", "--write", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
            ],
            ".tsx": [
                ("biome", ["biome", "format", "--write", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
            ],
            # CSS/SCSS (priority: biome → prettier)
            ".css": [
                ("biome", ["biome", "format", "--write", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
            ],
            ".scss": [
                ("biome", ["biome", "format", "--write", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
            ],
            # HTML (priority: prettier → biome)
            ".html": [
                ("prettier", ["prettier", "--write", "{input}"]),
                ("biome", ["biome", "format", "--write", "{input}"]),
            ],
            # JSON (priority: biome → prettier → jq)
            ".json": [
                ("biome", ["biome", "format", "--write", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
                ("jq", ["jq", ".", "{input}"]),  # Pretty JSON
            ],
            # TOML (priority: taplo → dprint)
            ".toml": [
                ("taplo", ["taplo", "fmt", "{input}"]),
                ("dprint", ["dprint", "fmt", "{input}"]),
            ],
            # YAML (priority: prettier → yq)
            ".yaml": [
                ("prettier", ["prettier", "--write", "{input}"]),
                ("yq", ["yq", "-i", "e", ".", "{input}"]),
            ],
            ".yml": [
                ("prettier", ["prettier", "--write", "{input}"]),
                ("yq", ["yq", "-i", "e", ".", "{input}"]),
            ],
            # Markdown (priority: dprint → prettier)
            ".md": [
                ("dprint", ["dprint", "fmt", "{input}"]),
                ("prettier", ["prettier", "--write", "{input}"]),
            ],
        }

        # Note: Command filtering is now done lazily when commands are requested

    def _filter_available_commands(
        self, commands: dict[str, list[tuple[str, list[str]]]]
    ) -> dict[str, list[tuple[str, list[str]]]]:
        """Filter command lists to only include available tools."""
        filtered = {}
        for ext, tool_list in commands.items():
            available_tools = [(tool, cmd) for tool, cmd in tool_list if self.is_available(tool)]
            if available_tools:  # Only include extensions with at least one available tool
                filtered[ext] = available_tools
        return filtered

    def is_available(self, tool: str) -> bool:
        """Check if a tool is available, using lazy detection if necessary."""
        return self._ensure_tool_detected(tool)

    def get_available_tools(self) -> list[str]:
        """Get list of all available tools."""
        return [tool for tool, available in self._tool_cache.items() if available]

    def get_minify_command(self, file_path: Path) -> tuple[str, list[str]] | None:
        """Get the best available minification command for a file with lazy tool detection."""
        ext = file_path.suffix.lower()
        raw_commands = self.minify_commands.get(ext, [])

        # Find first available tool for this extension
        for tool, command in raw_commands:
            if self.is_available(tool):  # This triggers lazy detection
                return tool, command

        return None

    def get_format_command(self, file_path: Path) -> tuple[str, list[str]] | None:
        """Get the best available formatting command for a file with lazy tool detection."""
        ext = file_path.suffix.lower()
        raw_commands = self.format_commands.get(ext, [])

        # Find first available tool for this extension
        for tool, command in raw_commands:
            if self.is_available(tool):  # This triggers lazy detection
                return tool, command

        return None

    def supports_minify(self, file_path: Path) -> bool:
        """Check if file type supports minification with lazy tool detection."""
        ext = file_path.suffix.lower()
        raw_commands = self.minify_commands.get(ext, [])

        # Check if any tool for this extension is available
        return any(self.is_available(tool) for tool, _ in raw_commands)

    def supports_format(self, file_path: Path) -> bool:
        """Check if file type supports formatting with lazy tool detection."""
        ext = file_path.suffix.lower()
        raw_commands = self.format_commands.get(ext, [])

        # Check if any tool for this extension is available
        return any(self.is_available(tool) for tool, _ in raw_commands)

    def execute_command(
        self, tool: str, command: list[str], input_file: Path, output_file: Path | None = None
    ) -> tuple[bool, str]:
        """
        Execute a tool command with simple error handling.

        Args:
            tool: Tool name
            command: Command template
            input_file: Input file path
            output_file: Output file path (if different from input)

        Returns:
            Tuple of (success, error_message)
        """
        return self._execute_single_command(tool, command, input_file, output_file)

    def _execute_single_command(
        self, tool: str, command: list[str], input_file: Path, output_file: Path | None = None
    ) -> tuple[bool, str]:
        """Execute a single tool command."""
        try:
            # Check if tool is still available (graceful degradation for partially broken tools)
            if not self._quick_tool_check(tool):
                return False, f"{tool} is no longer available"

            # Substitute placeholders
            if output_file:
                cmd = [
                    arg.replace("{input}", str(input_file)).replace("{output}", str(output_file))
                    for arg in command
                ]
            else:
                cmd = [
                    arg.replace("{input}", str(input_file)).replace("{output}", str(input_file))
                    for arg in command
                ]

            # Execute command with retries for transient errors
            max_retries = 2
            for attempt in range(max_retries + 1):
                try:
                    result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=30)

                    if result.returncode == 0:
                        # For stdout-based tools like jq, capture output and write to file
                        if tool == "jq" and output_file and result.stdout:
                            output_file.write_text(result.stdout)
                        return True, ""
                    error_msg = result.stderr or result.stdout or "Command failed"

                    # Check if this is a transient error worth retrying
                    if attempt < max_retries and self._is_transient_error(error_msg):
                        time.sleep(0.1 * (attempt + 1))  # Brief delay before retry
                        continue

                    return False, f"{tool}: {error_msg}"

                except subprocess.TimeoutExpired:
                    if attempt < max_retries:
                        continue
                    return False, f"{tool} timed out after 30 seconds"
                except PermissionError as e:
                    return False, f"{tool} permission error: {e!s}"
                except FileNotFoundError:
                    # Tool disappeared during execution
                    self._invalidate_tool_cache(tool)
                    return False, f"{tool} not found - tool may have been removed"
                except Exception as e:
                    if (
                        attempt < max_retries
                        and "resource temporarily unavailable" in str(e).lower()
                    ):
                        time.sleep(0.1 * (attempt + 1))
                        continue
                    return False, f"{tool} error: {e!s}"

            return False, f"{tool} failed after {max_retries + 1} attempts"

        except Exception as e:
            return False, f"{tool} unexpected error: {e!s}"

    def _quick_tool_check(self, tool: str) -> bool:
        """Quick check if tool is still available (for partially broken tools)."""
        try:
            # Quick which/where check (faster than version check)
            cmd = "where" if os.name == "nt" else "which"
            result = subprocess.run([cmd, tool], check=False, capture_output=True, timeout=1)
            return result.returncode == 0
        except Exception:
            return False

    def _is_transient_error(self, error_msg: str) -> bool:
        """Check if error message indicates a transient error worth retrying."""
        transient_indicators = [
            "resource temporarily unavailable",
            "device busy",
            "try again",
            "temporary failure",
            "connection reset",
            "network unreachable",
        ]
        error_lower = error_msg.lower()
        return any(indicator in error_lower for indicator in transient_indicators)

    def _invalidate_tool_cache(self, tool: str):
        """Invalidate cache for a specific tool that's no longer working."""
        if tool in self._tool_cache:
            self._tool_cache[tool] = False
            # Update persistent cache as well
            self._update_cache_with_tool(tool, False)

    def execute_command_with_fallback(
        self, file_path: Path, operation: str
    ) -> tuple[bool, str, str | None]:
        """
        Execute command with automatic fallback to next available tool.

        Args:
            file_path: File to process
            operation: 'minify' or 'format'

        Returns:
            Tuple of (success, error_message, tool_used)
        """
        if operation == "minify":
            commands = self.minify_commands.get(file_path.suffix.lower(), [])
        else:
            commands = self.format_commands.get(file_path.suffix.lower(), [])

        if not commands:
            return False, f"No {operation} tools available for {file_path.suffix}", None

        errors = []
        for tool, command_template in commands:
            if self.is_available(tool):
                # For in-place operations, pass file_path as output_file
                success, error_msg = self._execute_single_command(
                    tool, command_template, file_path, file_path
                )
                if success:
                    return True, "", tool

                errors.append(f"{tool}: {error_msg}")

                # If tool failed due to being unavailable, mark it as such
                if "not found" in error_msg or "no longer available" in error_msg:
                    self._invalidate_tool_cache(tool)

        # All tools failed
        return False, f"All {operation} tools failed - " + "; ".join(errors), None

    def get_minify_command_with_fallback(self, file_path: Path) -> list[tuple[str, list[str]]]:
        """Get all available minification commands for a file in priority order."""
        ext = file_path.suffix.lower()
        raw_commands = self.minify_commands.get(ext, [])

        # Return only tools that are currently available
        return [(tool, command) for tool, command in raw_commands if self.is_available(tool)]

    def get_format_command_with_fallback(self, file_path: Path) -> list[tuple[str, list[str]]]:
        """Get all available formatting commands for a file in priority order."""
        ext = file_path.suffix.lower()
        raw_commands = self.format_commands.get(ext, [])

        # Return only tools that are currently available
        return [(tool, command) for tool, command in raw_commands if self.is_available(tool)]

    def get_tool_info(self) -> dict[str, dict[str, any]]:
        """Get information about all tools for display."""
        tool_info = {
            # Fast tools (Rust/Go)
            "esbuild": {"type": "minifier", "language": "Go", "formats": ["JS", "TS"]},
            "swc": {"type": "minifier", "language": "Rust", "formats": ["JS", "TS"]},
            "biome": {
                "type": "formatter",
                "language": "Rust",
                "formats": ["JS", "TS", "JSON", "CSS"],
            },
            "ruff": {"type": "formatter", "language": "Rust", "formats": ["Python"]},
            "lightningcss": {"type": "minifier", "language": "Rust", "formats": ["CSS"]},
            "taplo": {"type": "formatter", "language": "Rust", "formats": ["TOML"]},
            "dprint": {"type": "formatter", "language": "Rust", "formats": ["Multiple"]},
            # Standard tools
            "terser": {"type": "minifier", "language": "Node.js", "formats": ["JS"]},
            "prettier": {"type": "formatter", "language": "Node.js", "formats": ["Multiple"]},
            "black": {"type": "formatter", "language": "Python", "formats": ["Python"]},
            "jq": {"type": "processor", "language": "C", "formats": ["JSON"]},
            "yq": {"type": "processor", "language": "Go", "formats": ["YAML"]},
            "html-minifier-terser": {
                "type": "minifier",
                "language": "Node.js",
                "formats": ["HTML"],
            },
        }

        # Add availability info
        result = {}
        for tool, info in tool_info.items():
            result[tool] = {**info, "available": self.is_available(tool)}

        return result


def detect_file_type(file_path: Path) -> str | None:
    """Simple file type detection based on extension."""
    ext = file_path.suffix.lower()

    type_mapping = {
        # JavaScript/TypeScript
        ".js": "javascript",
        ".mjs": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        # Styles
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        # Markup
        ".html": "html",
        ".htm": "html",
        ".xml": "xml",
        ".svg": "svg",
        # Data
        ".json": "json",
        ".jsonc": "jsonc",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        # Code
        ".py": "python",
        ".md": "markdown",
        ".graphql": "graphql",
    }

    return type_mapping.get(ext)


def get_available_tools() -> list[str]:
    """Get list of available tools (convenience function)."""
    manager = ToolManager()
    return manager.get_available_tools()
