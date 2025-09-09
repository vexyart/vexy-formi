#!/usr/bin/env python3
# this_file: src/vexy_formi/tools_update.py
"""
VexyFormi Tool Updater - Robust updating of installed minifiers and formatters

This module updates all installed VexyFormi tools to their latest versions,
ensuring optimal performance and latest features.
"""

import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
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


@dataclass
class ToolInfo:
    """Information about an installed tool."""

    name: str
    current_version: str | None
    latest_version: str | None
    update_method: str
    update_command: list[str]
    check_command: list[str]
    description: str


class ToolUpdater:
    """Robust updater for minification and formatting tools."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.tools: list[ToolInfo] = []
        self.updated_tools = []
        self.failed_updates = []
        self.homebrew_available = self._check_homebrew()
        self.node_available = self._check_node()
        self.cargo_available = self._check_cargo()

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

    def _run_command(
        self, cmd: list[str], description: str, critical: bool = True, timeout: int = 300
    ) -> tuple[bool, str]:
        """Run a command with error handling and return success status and output."""
        try:
            if self.verbose:
                console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")

            result = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=timeout)

            if result.returncode == 0:
                if self.verbose and result.stdout.strip():
                    console.print(f"[dim]{result.stdout.strip()}[/dim]")
                return True, result.stdout.strip()
            error_msg = f"Failed {description}: {result.stderr.strip()}"
            if critical:
                console.print(f"[red]{error_msg}[/red]")
            else:
                console.print(f"[yellow]{error_msg}[/yellow]")
            return False, result.stderr.strip()

        except subprocess.TimeoutExpired:
            console.print(f"[red]Timeout: {description} took too long[/red]")
            return False, "Timeout"
        except Exception as e:
            console.print(f"[red]Error running {description}: {e!s}[/red]")
            return False, str(e)

    def _get_version(self, check_cmd: list[str]) -> str | None:
        """Get version of a tool."""
        try:
            result = subprocess.run(check_cmd, check=False, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Extract version from output (varies by tool)
                output = result.stdout.strip()
                # Try common patterns
                import re

                version_patterns = [
                    r"v?(\d+\.\d+\.\d+)",  # Standard semver
                    r"version\s+(\d+\.\d+\.\d+)",  # "version 1.2.3"
                    r"(\d+\.\d+\.\d+)",  # Just numbers
                ]

                for pattern in version_patterns:
                    match = re.search(pattern, output)
                    if match:
                        return match.group(1)

                return output[:20]  # First 20 chars if no pattern matches
            return None
        except Exception:
            return None

    def discover_tools(self) -> None:
        """Discover installed tools and their versions."""
        console.print(Panel("Discovering Installed Tools", style="blue"))

        # Define tools with their update methods
        tool_definitions = [
            # Homebrew tools
            {
                "name": "dprint",
                "check_cmd": ["dprint", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "dprint"],
                "description": "Universal pluggable formatter (Rust)",
            },
            {
                "name": "biome",
                "check_cmd": ["biome", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "biome"],
                "description": "Fast web formatter/linter (Rust)",
            },
            {
                "name": "esbuild",
                "check_cmd": ["esbuild", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "esbuild"],
                "description": "Ultra-fast bundler/minifier (Go)",
            },
            {
                "name": "ruff",
                "check_cmd": ["ruff", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "ruff"],
                "description": "Fast Python formatter/linter (Rust)",
            },
            {
                "name": "jq",
                "check_cmd": ["jq", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "jq"],
                "description": "JSON processor",
            },
            {
                "name": "yq",
                "check_cmd": ["yq", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "yq"],
                "description": "YAML/JSON/XML processor",
            },
            {
                "name": "taplo",
                "check_cmd": ["taplo", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "taplo"],
                "description": "TOML formatter/validator (Rust)",
            },
            {
                "name": "minify",
                "check_cmd": ["minify", "--version"],
                "update_method": "homebrew",
                "update_cmd": ["brew", "upgrade", "minify"],
                "description": "Universal web minifier (Go)",
            },
            # NPM global tools
            {
                "name": "swc",
                "check_cmd": ["swc", "--version"],
                "update_method": "npm",
                "update_cmd": ["npm", "update", "-g", "@swc/cli", "@swc/core"],
                "description": "Fast JS/TS compiler/minifier (Rust)",
            },
            {
                "name": "terser",
                "check_cmd": ["terser", "--version"],
                "update_method": "npm",
                "update_cmd": ["npm", "update", "-g", "terser"],
                "description": "JavaScript minifier",
            },
            {
                "name": "lightningcss",
                "check_cmd": ["lightningcss", "--version"],
                "update_method": "npm",
                "update_cmd": ["npm", "update", "-g", "lightningcss-cli"],
                "description": "Ultra-fast CSS minifier (Rust)",
            },
            {
                "name": "prettier",
                "check_cmd": ["prettier", "--version"],
                "update_method": "npm",
                "update_cmd": ["npm", "update", "-g", "prettier"],
                "description": "Code formatter",
            },
            {
                "name": "html-minifier-terser",
                "check_cmd": ["html-minifier-terser", "--version"],
                "update_method": "npm",
                "update_cmd": ["npm", "update", "-g", "html-minifier-terser"],
                "description": "HTML minifier",
            },
            # Cargo tools
            {
                "name": "minhtml",
                "check_cmd": ["minhtml", "--version"],
                "update_method": "cargo",
                "update_cmd": ["cargo", "install", "minhtml", "--force"],
                "description": "Fast HTML minifier (Rust)",
            },
        ]

        # Check which tools are installed
        for tool_def in tool_definitions:
            current_version = self._get_version(tool_def["check_cmd"])
            if current_version:
                tool = ToolInfo(
                    name=tool_def["name"],
                    current_version=current_version,
                    latest_version=None,  # Will be fetched during update check
                    update_method=tool_def["update_method"],
                    update_command=tool_def["update_cmd"],
                    check_command=tool_def["check_cmd"],
                    description=tool_def["description"],
                )
                self.tools.append(tool)
                console.print(f"[green]✓ Found {tool.name} v{current_version}[/green]")
            else:
                console.print(f"[dim]- {tool_def['name']} not found[/dim]")

        console.print(f"\n[bold]Found {len(self.tools)} installed tools[/bold]")

    def update_package_managers(self) -> None:
        """Update package managers themselves."""
        console.print(Panel("Updating Package Managers", style="yellow"))

        # Update Homebrew
        if self.homebrew_available:
            console.print("[yellow]Updating Homebrew...[/yellow]")
            success, _ = self._run_command(["brew", "update"], "Homebrew update", critical=False)
            if success:
                console.print("[green]✓ Homebrew updated[/green]")
            else:
                console.print("[yellow]⚠ Homebrew update failed[/yellow]")

        # Update npm
        if self.node_available:
            console.print("[yellow]Updating npm...[/yellow]")
            success, _ = self._run_command(
                ["npm", "update", "-g", "npm"], "npm update", critical=False
            )
            if success:
                console.print("[green]✓ npm updated[/green]")
            else:
                console.print("[yellow]⚠ npm update failed[/yellow]")

        # Update Rust
        if self.cargo_available:
            console.print("[yellow]Updating Rust toolchain...[/yellow]")
            success, _ = self._run_command(["rustup", "update"], "Rust update", critical=False)
            if success:
                console.print("[green]✓ Rust updated[/green]")
            else:
                console.print("[yellow]⚠ Rust update failed[/yellow]")

    def update_tools(self) -> None:
        """Update all discovered tools."""
        if not self.tools:
            console.print("[yellow]No tools found to update[/yellow]")
            return

        console.print(Panel("Updating Tools", style="green"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Updating tools...", total=len(self.tools))

            for tool in self.tools:
                progress.update(task, description=f"Updating {tool.name}")

                # Skip if package manager not available
                if tool.update_method == "homebrew" and not self.homebrew_available:
                    console.print(f"[yellow]Skipping {tool.name} (Homebrew not available)[/yellow]")
                    progress.advance(task)
                    continue
                if tool.update_method == "npm" and not self.node_available:
                    console.print(f"[yellow]Skipping {tool.name} (npm not available)[/yellow]")
                    progress.advance(task)
                    continue
                if tool.update_method == "cargo" and not self.cargo_available:
                    console.print(f"[yellow]Skipping {tool.name} (cargo not available)[/yellow]")
                    progress.advance(task)
                    continue

                # Update the tool
                success, output = self._run_command(
                    tool.update_command,
                    f"{tool.name} update",
                    critical=False,
                    timeout=600,  # 10 minutes for large updates
                )

                if success:
                    # Get new version
                    new_version = self._get_version(tool.check_command)
                    tool.latest_version = new_version

                    if new_version != tool.current_version:
                        console.print(
                            f"[green]✓ {tool.name} updated: {tool.current_version} → {new_version}[/green]"
                        )
                        self.updated_tools.append(tool)
                    else:
                        console.print(
                            f"[dim]• {tool.name} already up to date ({tool.current_version})[/dim]"
                        )
                else:
                    console.print(f"[red]✗ {tool.name} update failed[/red]")
                    self.failed_updates.append(tool)

                progress.advance(task)

    def cleanup_caches(self) -> None:
        """Clean up package manager caches."""
        console.print(Panel("Cleaning Up Caches", style="cyan"))

        cleanup_commands = []

        if self.homebrew_available:
            cleanup_commands.append((["brew", "cleanup"], "Homebrew cleanup"))

        if self.node_available:
            cleanup_commands.append((["npm", "cache", "clean", "--force"], "npm cache cleanup"))

        if self.cargo_available:
            cleanup_commands.append((["cargo", "cache", "--autoclean"], "Cargo cache cleanup"))

        for cmd, description in cleanup_commands:
            success, _ = self._run_command(cmd, description, critical=False, timeout=120)
            if success:
                console.print(f"[green]✓ {description} completed[/green]")
            else:
                console.print(f"[yellow]⚠ {description} failed (non-critical)[/yellow]")

    def verify_installations(self) -> None:
        """Verify all tools are working after updates."""
        console.print(Panel("Verifying Installations", style="purple"))

        broken_tools = []

        for tool in self.tools:
            success, _ = self._run_command(
                tool.check_command, f"{tool.name} verification", critical=False, timeout=30
            )
            if success:
                console.print(f"[green]✓ {tool.name} working correctly[/green]")
            else:
                console.print(f"[red]✗ {tool.name} verification failed[/red]")
                broken_tools.append(tool)

        if broken_tools:
            console.print(f"\n[red]{len(broken_tools)} tools failed verification[/red]")
            console.print("Consider reinstalling these tools with 'vfor install'")

    def update_config_files(self) -> None:
        """Update configuration files with latest recommendations."""
        console.print(Panel("Updating Configuration Files", style="yellow"))

        config_updates = {
            "dprint.json": {
                "backup": True,
                "description": "dprint configuration with latest plugins",
                "updates": {
                    "plugins": [
                        "https://plugins.dprint.dev/typescript-0.91.1.wasm",
                        "https://plugins.dprint.dev/json-0.19.3.wasm",
                        "https://plugins.dprint.dev/markdown-0.17.2.wasm",
                        "https://plugins.dprint.dev/toml-0.6.2.wasm",
                    ]
                },
            }
        }

        for filename, config_info in config_updates.items():
            filepath = Path(filename)
            if filepath.exists():
                try:
                    # Backup existing config
                    if config_info["backup"]:
                        backup_path = filepath.with_suffix(
                            f"{filepath.suffix}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                        )
                        shutil.copy2(filepath, backup_path)
                        console.print(f"[dim]Backed up {filename} to {backup_path.name}[/dim]")

                    # Update config
                    with open(filepath) as f:
                        current_config = json.load(f)

                    # Apply updates
                    for key, value in config_info["updates"].items():
                        current_config[key] = value

                    # Write updated config
                    with open(filepath, "w") as f:
                        json.dump(current_config, f, indent=2)

                    console.print(f"[green]✓ Updated {config_info['description']}[/green]")

                except Exception as e:
                    console.print(f"[yellow]⚠ Failed to update {filename}: {e!s}[/yellow]")
            else:
                console.print(f"[dim]• {filename} not found, skipping[/dim]")

    def print_summary(self) -> None:
        """Print update summary."""
        console.print(Panel("Update Summary", style="bold blue"))

        # Create summary table
        table = Table(title="Tool Update Results")
        table.add_column("Tool", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Version Change")
        table.add_column("Description")

        # Add updated tools
        for tool in self.updated_tools:
            table.add_row(
                tool.name,
                "✓ Updated",
                f"{tool.current_version} → {tool.latest_version}",
                tool.description,
            )

        # Add failed updates
        for tool in self.failed_updates:
            table.add_row(
                tool.name, "✗ Failed", tool.current_version or "unknown", tool.description
            )

        # Add unchanged tools
        unchanged_tools = [
            t for t in self.tools if t not in self.updated_tools and t not in self.failed_updates
        ]
        for tool in unchanged_tools:
            table.add_row(
                tool.name, "• Current", tool.current_version or "unknown", tool.description
            )

        console.print(table)

        # Statistics
        total_tools = len(self.tools)
        updated_count = len(self.updated_tools)
        failed_count = len(self.failed_updates)
        current_count = total_tools - updated_count - failed_count

        stats_text = f"""
[green]Updated: {updated_count}[/green]
[yellow]Current: {current_count}[/yellow]
[red]Failed: {failed_count}[/red]
[bold]Total: {total_tools}[/bold]
"""

        console.print(Panel(stats_text, title="Statistics"))

        # Next steps
        if self.updated_tools:
            console.print(
                Panel(
                    "Tools have been updated! You can now use:\n"
                    "• Latest performance improvements\n"
                    "• New features and bug fixes\n"
                    "• Enhanced compatibility\n\n"
                    "Run 'vfor tools' to see all tool versions",
                    title="Update Complete! 🎉",
                    style="green",
                )
            )
        elif not self.failed_updates:
            console.print(
                Panel(
                    "All tools are already up to date!\nYour VexyFormi installation is current.",
                    title="Already Current ✨",
                    style="blue",
                )
            )


def update_tools(verbose: bool = False) -> None:
    """Main update function."""
    console.print(
        Panel(
            "VexyFormi Tool Updater\n"
            "Updating all installed minifiers and formatters to latest versions",
            title="🔄 VexyFormi Update",
            style="bold blue",
        )
    )

    updater = ToolUpdater(verbose=verbose)

    try:
        # Discover installed tools
        updater.discover_tools()

        if not updater.tools:
            console.print("[yellow]No VexyFormi tools found. Run 'vfor install' first.[/yellow]")
            return

        # Update package managers
        updater.update_package_managers()

        # Update all tools
        updater.update_tools()

        # Clean up caches
        updater.cleanup_caches()

        # Verify installations
        updater.verify_installations()

        # Update config files
        updater.update_config_files()

        # Print summary
        updater.print_summary()

        console.print("[bold green]Update completed! 🎉[/bold green]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Update cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Update failed: {e!s}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    update_tools(verbose="--verbose" in sys.argv)
