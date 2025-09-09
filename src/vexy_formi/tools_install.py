#!/usr/bin/env python3
# this_file: src/vexy_formi/tools_install.py
"""
VexyFormi Tool Installer - Robust installation of high-performance minifiers and formatters

This module installs the fastest and most efficient minifiers and formatters available,
prioritizing Rust and Go-based tools for maximum performance.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

console = Console()


class ToolInstaller:
    """Robust installer for minification and formatting tools."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.installed_tools = []
        self.failed_tools = []
        self.arch = self._detect_architecture()
        self.homebrew_available = self._check_homebrew()
        self.node_available = self._check_node()
        self.cargo_available = self._check_cargo()

    def _detect_architecture(self) -> str:
        """Detect system architecture (x64 or arm64)."""
        machine = platform.machine().lower()
        if machine in ["arm64", "aarch64"]:
            return "arm64"
        if machine in ["x86_64", "amd64"]:
            return "x64"
        console.print(
            f"[yellow]Warning: Unknown architecture {machine}, defaulting to x64[/yellow]"
        )
        return "x64"

    def _check_homebrew(self) -> bool:
        """Check if Homebrew is available."""
        try:
            result = subprocess.run(["which", "brew"], check=False, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _check_node(self) -> bool:
        """Check if Node.js/npm is available."""
        try:
            result = subprocess.run(["which", "npm"], check=False, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _check_cargo(self) -> bool:
        """Check if Rust/Cargo is available."""
        try:
            result = subprocess.run(["which", "cargo"], check=False, capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

    def _run_command(self, cmd: list[str], description: str, critical: bool = True) -> bool:
        """Run a command with error handling."""
        try:
            if self.verbose:
                console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(
                cmd,
                check=False, capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                if self.verbose and result.stdout.strip():
                    console.print(f"[dim]{result.stdout.strip()}[/dim]")
                return True
            error_msg = f"Failed {description}: {result.stderr.strip()}"
            if critical:
                console.print(f"[red]{error_msg}[/red]")
            else:
                console.print(f"[yellow]{error_msg}[/yellow]")
            return False

        except subprocess.TimeoutExpired:
            console.print(f"[red]Timeout: {description} took too long[/red]")
            return False
        except Exception as e:
            console.print(f"[red]Error running {description}: {e!s}[/red]")
            return False

    def install_prerequisites(self) -> bool:
        """Install or verify prerequisites."""
        console.print(Panel("Installing Prerequisites", style="blue"))

        success = True

        # Install Homebrew if not available (macOS/Linux)
        if not self.homebrew_available and platform.system() in ["Darwin", "Linux"]:
            console.print("[yellow]Installing Homebrew...[/yellow]")
            install_cmd = [
                "/bin/bash",
                "-c",
                "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)",
            ]
            if self._run_command(install_cmd, "Homebrew installation", critical=False):
                self.homebrew_available = True
                console.print("[green]✓ Homebrew installed[/green]")
            else:
                console.print("[red]✗ Homebrew installation failed[/red]")
                success = False
        else:
            console.print("[green]✓ Homebrew already available[/green]")

        # Install Node.js if not available and Homebrew is available
        if not self.node_available and self.homebrew_available:
            console.print("[yellow]Installing Node.js...[/yellow]")
            if self._run_command(["brew", "install", "node"], "Node.js installation"):
                self.node_available = True
                console.print("[green]✓ Node.js installed[/green]")
            else:
                console.print(
                    "[yellow]Node.js installation failed, some tools may not be available[/yellow]"
                )
        elif self.node_available:
            console.print("[green]✓ Node.js already available[/green]")

        # Install Rust if not available
        if not self.cargo_available:
            console.print("[yellow]Installing Rust (cargo)...[/yellow]")
            # Use shell=True for this complex command
            try:
                result = subprocess.run(
                    "curl --proto =https --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y",
                    check=False, shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                if result.returncode == 0:
                    # Source the cargo environment
                    cargo_path = Path.home() / ".cargo" / "bin"
                    os.environ["PATH"] = f"{cargo_path}:{os.environ.get('PATH', '')}"
                    self.cargo_available = True
                    console.print("[green]✓ Rust installed[/green]")
                else:
                    console.print(
                        "[yellow]Rust installation failed, some tools may not be available[/yellow]"
                    )
            except Exception:
                console.print(
                    "[yellow]Rust installation failed, some tools may not be available[/yellow]"
                )
        else:
            console.print("[green]✓ Rust already available[/green]")

        return success

    def install_universal_tools(self) -> None:
        """Install universal/multi-format tools."""
        console.print(Panel("Installing Universal/Multi-Format Tools", style="green"))

        tools = [
            # dprint - Universal formatter (Rust)
            {
                "name": "dprint",
                "method": "homebrew",
                "cmd": ["brew", "install", "dprint"],
                "description": "Universal pluggable formatter (Rust)",
                "test_cmd": ["dprint", "--version"],
            },
            # Biome - Web formatter/linter (Rust)
            {
                "name": "biome",
                "method": "homebrew",
                "cmd": ["brew", "install", "biome"],
                "description": "Fast web formatter/linter (Rust)",
                "test_cmd": ["biome", "--version"],
            },
            # esbuild - Fast bundler/minifier (Go)
            {
                "name": "esbuild",
                "method": "homebrew",
                "cmd": ["brew", "install", "esbuild"],
                "description": "Ultra-fast bundler/minifier (Go)",
                "test_cmd": ["esbuild", "--version"],
            },
        ]

        self._install_tools(tools)

    def install_language_specific_tools(self) -> None:
        """Install language-specific tools."""
        console.print(Panel("Installing Language-Specific Tools", style="cyan"))

        tools = [
            # Python - Ruff (formatter + linter)
            {
                "name": "ruff",
                "method": "homebrew",
                "cmd": ["brew", "install", "ruff"],
                "description": "Fast Python formatter/linter (Rust)",
                "test_cmd": ["ruff", "--version"],
            },
            # JSON/YAML processors
            {
                "name": "jq",
                "method": "homebrew",
                "cmd": ["brew", "install", "jq"],
                "description": "JSON processor",
                "test_cmd": ["jq", "--version"],
            },
            {
                "name": "yq",
                "method": "homebrew",
                "cmd": ["brew", "install", "yq"],
                "description": "YAML/JSON/XML processor",
                "test_cmd": ["yq", "--version"],
            },
            # TOML - Taplo
            {
                "name": "taplo",
                "method": "homebrew",
                "cmd": ["brew", "install", "taplo"],
                "description": "TOML formatter/validator (Rust)",
                "test_cmd": ["taplo", "--version"],
            },
        ]

        self._install_tools(tools)

    def install_performance_tools(self) -> None:
        """Install high-performance minification tools."""
        console.print(Panel("Installing High-Performance Minification Tools", style="magenta"))

        tools = []

        # Node.js based tools (if Node is available)
        if self.node_available:
            node_tools = [
                {
                    "name": "SWC",
                    "method": "npm",
                    "cmd": ["npm", "install", "-g", "@swc/cli", "@swc/core"],
                    "description": "Fast JS/TS compiler/minifier (Rust via Node)",
                    "test_cmd": ["swc", "--version"],
                },
                {
                    "name": "Terser",
                    "method": "npm",
                    "cmd": ["npm", "install", "-g", "terser"],
                    "description": "JavaScript minifier",
                    "test_cmd": ["terser", "--version"],
                },
                {
                    "name": "Lightning CSS CLI",
                    "method": "npm",
                    "cmd": ["npm", "install", "-g", "lightningcss-cli"],
                    "description": "Ultra-fast CSS minifier (Rust)",
                    "test_cmd": ["lightningcss", "--version"],
                },
                {
                    "name": "Prettier",
                    "method": "npm",
                    "cmd": ["npm", "install", "-g", "prettier"],
                    "description": "Code formatter",
                    "test_cmd": ["prettier", "--version"],
                },
                {
                    "name": "html-minifier-terser",
                    "method": "npm",
                    "cmd": ["npm", "install", "-g", "html-minifier-terser"],
                    "description": "HTML minifier",
                    "test_cmd": ["html-minifier-terser", "--version"],
                },
            ]
            tools.extend(node_tools)

        # Rust-based tools (if Cargo is available)
        if self.cargo_available:
            rust_tools = [
                {
                    "name": "minify-html",
                    "method": "cargo",
                    "cmd": ["cargo", "install", "minhtml"],
                    "description": "Fast HTML minifier (Rust)",
                    "test_cmd": ["minhtml", "--version"],
                },
            ]
            tools.extend(rust_tools)

        # Go-based tools
        go_tools = [
            {
                "name": "TDEWolff minify",
                "method": "homebrew",
                "cmd": ["brew", "install", "minify"],
                "description": "Universal web minifier (Go)",
                "test_cmd": ["minify", "--version"],
            },
        ]
        tools.extend(go_tools)

        if tools:
            self._install_tools(tools)
        else:
            console.print("[yellow]No package managers available for performance tools[/yellow]")

    def _install_tools(self, tools: list[dict]) -> None:
        """Install a list of tools with progress tracking."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Installing tools...", total=len(tools))

            for tool in tools:
                progress.update(task, description=f"Installing {tool['name']}")

                # Check if already installed
                if self._check_tool_installed(tool.get("test_cmd", [])):
                    console.print(f"[green]✓ {tool['name']} already installed[/green]")
                    self.installed_tools.append(tool["name"])
                    progress.advance(task)
                    continue

                # Install the tool
                method = tool["method"]
                if method == "homebrew" and not self.homebrew_available:
                    console.print(
                        f"[yellow]Skipping {tool['name']} (Homebrew not available)[/yellow]"
                    )
                    progress.advance(task)
                    continue
                if method == "npm" and not self.node_available:
                    console.print(f"[yellow]Skipping {tool['name']} (npm not available)[/yellow]")
                    progress.advance(task)
                    continue
                if method == "cargo" and not self.cargo_available:
                    console.print(f"[yellow]Skipping {tool['name']} (cargo not available)[/yellow]")
                    progress.advance(task)
                    continue

                if self._run_command(tool["cmd"], f"{tool['name']} installation", critical=False):
                    # Verify installation
                    if self._check_tool_installed(tool.get("test_cmd", [])):
                        console.print(f"[green]✓ {tool['name']} installed successfully[/green]")
                        self.installed_tools.append(tool["name"])
                    else:
                        console.print(
                            f"[yellow]⚠ {tool['name']} installed but verification failed[/yellow]"
                        )
                        self.failed_tools.append(tool["name"])
                else:
                    console.print(f"[red]✗ {tool['name']} installation failed[/red]")
                    self.failed_tools.append(tool["name"])

                progress.advance(task)

    def _check_tool_installed(self, test_cmd: list[str]) -> bool:
        """Check if a tool is properly installed."""
        if not test_cmd:
            return False

        try:
            result = subprocess.run(test_cmd, check=False, capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except Exception:
            return False

    def create_config_files(self) -> None:
        """Create default configuration files for installed tools."""
        console.print(Panel("Creating Configuration Files", style="yellow"))

        configs = {
            "dprint.json": {
                "description": "dprint configuration",
                "content": {
                    "typescript": {"indentWidth": 2, "quoteStyle": "preferDouble"},
                    "json": {"indentWidth": 2},
                    "markdown": {"textWrap": "maintain"},
                    "toml": {},
                    "includes": ["**/*.{ts,tsx,js,jsx,json,md,toml}"],
                    "excludes": ["node_modules", "target", ".git", "dist", "build"],
                    "plugins": [
                        "https://plugins.dprint.dev/typescript-0.91.1.wasm",
                        "https://plugins.dprint.dev/json-0.19.3.wasm",
                        "https://plugins.dprint.dev/markdown-0.17.2.wasm",
                        "https://plugins.dprint.dev/toml-0.6.2.wasm",
                    ],
                },
            },
            "biome.json": {
                "description": "Biome configuration",
                "content": {
                    "files": {
                        "include": ["**/*.{js,jsx,ts,tsx,json,jsonc}"],
                        "ignore": ["node_modules", "dist", "build", ".git"],
                    },
                    "formatter": {"enabled": True, "indentStyle": "space", "indentWidth": 2},
                    "linter": {"enabled": True, "rules": {"recommended": True}},
                },
            },
            "ruff.toml": {
                "description": "Ruff configuration",
                "content": """# Ruff configuration
[tool.ruff]
line-length = 88
target-version = "py312"

[tool.ruff.format]
quote-style = "double"
indent-style = "space"

[tool.ruff.lint]
select = [
    "E",  # pycodestyle errors
    "W",  # pycodestyle warnings
    "F",  # Pyflakes
    "I",  # isort
    "B",  # flake8-bugbear
    "C4", # flake8-comprehensions
    "UP", # pyupgrade
]
ignore = []

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]
""",
            },
            ".vfor.json": {
                "description": "VexyFormi configuration",
                "content": {
                    "preferred_js_tool": "esbuild",
                    "preferred_css_tool": "biome",
                    "preferred_python_tool": "ruff",
                    "max_workers": 4,
                    "create_backup": True,
                    "backup_dir": ".vfor_backups",
                },
            },
        }

        for filename, config in configs.items():
            try:
                filepath = Path(filename)
                if not filepath.exists():
                    if filename.endswith(".json"):
                        with open(filepath, "w") as f:
                            json.dump(config["content"], f, indent=2)
                    else:
                        with open(filepath, "w") as f:
                            f.write(config["content"])

                    console.print(f"[green]✓ Created {config['description']}: {filename}[/green]")
                else:
                    console.print(f"[dim]• {filename} already exists[/dim]")
            except Exception as e:
                console.print(f"[yellow]⚠ Failed to create {filename}: {e!s}[/yellow]")

    def print_summary(self) -> None:
        """Print installation summary."""
        console.print(Panel("Installation Summary", style="bold blue"))

        # Create summary table
        table = Table(title="Installed Tools")
        table.add_column("Tool", style="green")
        table.add_column("Status", style="bold")
        table.add_column("Purpose")

        # Add installed tools
        for tool in self.installed_tools:
            table.add_row(tool, "✓ Installed", self._get_tool_purpose(tool))

        # Add failed tools
        for tool in self.failed_tools:
            table.add_row(tool, "✗ Failed", self._get_tool_purpose(tool))

        console.print(table)

        # Print next steps
        if self.installed_tools:
            console.print(
                Panel(
                    "Next Steps:\n"
                    "1. Run 'vfor update' to update all tools\n"
                    "2. Use 'vfor mini <directory>' for minification\n"
                    "3. Use 'vfor fmt <directory>' for formatting\n"
                    "4. Check tool versions with 'vfor tools'",
                    title="Ready to Use!",
                    style="green",
                )
            )

    def _get_tool_purpose(self, tool: str) -> str:
        """Get the purpose description for a tool."""
        purposes = {
            "dprint": "Universal formatter",
            "biome": "Web formatter/linter",
            "esbuild": "Fast bundler/minifier",
            "ruff": "Python formatter/linter",
            "jq": "JSON processor",
            "yq": "YAML processor",
            "taplo": "TOML formatter",
            "SWC": "JS/TS compiler/minifier",
            "Terser": "JS minifier",
            "Lightning CSS CLI": "CSS minifier",
            "minify-html": "HTML minifier",
            "TDEWolff minify": "Universal minifier",
            "Prettier": "Code formatter",
            "html-minifier-terser": "HTML minifier",
        }
        return purposes.get(tool, "Code tool")


def install_tools(verbose: bool = False) -> None:
    """Main installation function."""
    console.print(
        Panel(
            "VexyFormi Tool Installer\nInstalling high-performance minifiers and formatters",
            title="🚀 VexyFormi Setup",
            style="bold blue",
        )
    )

    installer = ToolInstaller(verbose=verbose)

    try:
        # Check system
        console.print(f"[dim]System: {platform.system()} {installer.arch}[/dim]")

        # Install prerequisites
        installer.install_prerequisites()

        # Install tools in categories
        installer.install_universal_tools()
        installer.install_language_specific_tools()
        installer.install_performance_tools()

        # Create config files
        installer.create_config_files()

        # Print summary
        installer.print_summary()

        console.print("[bold green]Installation completed! 🎉[/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Installation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Installation failed: {e!s}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    install_tools(verbose="--verbose" in sys.argv)
