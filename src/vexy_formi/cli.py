#!/usr/bin/env python3
# this_file: src/vexy_formi/cli.py
"""
Command-line interface for VexyFormi.

Simple, fast CLI for code formatting and minification using the best available tools.
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Optional

import fire
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from .config import Config, create_example_config_file
from .core import FileProcessor
from .tools import ToolManager
from .tools_install import install_tools
from .tools_update import update_tools

console = Console()


class VFor:
    """VFor - Fast code formatting and minification tool."""

    def __init__(self):
        self.config = Config()
        self.processor = FileProcessor(self.config)
        self.tool_manager = ToolManager(self.config)

    def mini(
        self,
        path: str = ".",
        *,
        recursive: bool = True,
        exclude: list[str] | None = None,
        verbose: bool = False,
        backup: bool = True,
        dry_run: bool = False,
        force: bool = False,
    ):
        """
        Minify files using the fastest available tools.

        Args:
            path: Directory or file path to minify (default: current directory)
            recursive: Process directories recursively (default: True)
            exclude: Glob patterns to exclude (e.g., ["*.test.js", "node_modules/**"])
            verbose: Show detailed progress information (default: False)
            backup: Create backup files before processing (default: True)
            dry_run: Preview changes without modifying files (default: False)
            force: Skip safety warnings and confirmations (default: False)
        """
        if verbose:
            backup_text = "with backup" if backup and not dry_run else "no backup"
            dry_text = " (dry run)" if dry_run else ""
            console.print(f"Minifying {Path(path).resolve()}{dry_text} - {backup_text}")

        # Process files with enhanced progress reporting
        exclude_patterns = self.config.merge_exclude_patterns(exclude)

        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            progress_task = None
            start_time = time.time()
            successful_files = 0
            failed_files = 0
            total_size_before = 0
            total_size_after = 0

            def progress_callback(result, completed, total):
                nonlocal \
                    progress_task, \
                    successful_files, \
                    failed_files, \
                    total_size_before, \
                    total_size_after

                if progress_task is None:
                    progress_task = progress.add_task("Minifying files...", total=total)

                # Update counters
                if result.success:
                    successful_files += 1
                else:
                    failed_files += 1

                total_size_before += result.original_size
                total_size_after += result.final_size

                # Update progress description with current file and stats
                elapsed_time = time.time() - start_time
                rate = completed / elapsed_time if elapsed_time > 0 else 0
                size_saved = total_size_before - total_size_after
                size_saved_mb = size_saved / (1024 * 1024)

                description = f"Minifying files ({successful_files} ✓, {failed_files} ✗) | {size_saved_mb:.1f}MB saved | {rate:.1f} files/s"
                progress.update(progress_task, completed=completed, description=description)

                if verbose:
                    status = "✓" if result.success else "✗"
                    file_name = result.path.name
                    if result.success and not dry_run:
                        reduction = f" ({result.size_reduction_percent:+.1f}%)"
                    else:
                        reduction = (
                            " (preview)" if dry_run else " (error)" if result.error_message else ""
                        )
                    console.print(f"  {status} {file_name}{reduction}")

            # Safety checks before processing
            target_path = Path(path)
            if not force and not dry_run:
                # Discover files first for safety analysis
                extensions = set(self.processor.tool_manager.minify_commands.keys())
                files_to_process = self.processor.file_handler.find_files(
                    target_path, extensions, exclude_patterns, recursive, lazy_validation=True
                )

                if files_to_process:
                    from .safety import SafetyChecker, get_user_confirmation

                    safety_checker = SafetyChecker()
                    summary = safety_checker.get_operation_summary(
                        files_to_process, "minify", dry_run
                    )

                    if not get_user_confirmation("minify", summary):
                        console.print("Operation cancelled")
                        return

            result = self.processor.minify_files(
                target_path,
                recursive=recursive,
                exclude_patterns=exclude_patterns,
                max_workers=self.config.get("max_workers", 4),
                create_backup=backup,
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

        self._display_results(result, "minification", verbose, dry_run)

    def fmt(
        self,
        path: str = ".",
        *,
        recursive: bool = True,
        exclude: list[str] | None = None,
        verbose: bool = False,
        backup: bool = True,
        dry_run: bool = False,
        force: bool = False,
    ):
        """
        Format files using the fastest available tools.

        Args:
            path: Directory or file path to format (default: current directory)
            recursive: Process directories recursively (default: True)
            exclude: Glob patterns to exclude (e.g., ["*.min.js", "dist/**"])
            verbose: Show detailed progress information (default: False)
            backup: Create backup files before processing (default: True)
            dry_run: Preview changes without modifying files (default: False)
            force: Skip safety warnings and confirmations (default: False)
        """
        if verbose:
            backup_text = "with backup" if backup and not dry_run else "no backup"
            dry_text = " (dry run)" if dry_run else ""
            console.print(f"Formatting {Path(path).resolve()}{dry_text} - {backup_text}")

        # Process files with enhanced progress reporting
        exclude_patterns = self.config.merge_exclude_patterns(exclude)

        # Create progress display
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            progress_task = None
            start_time = time.time()
            successful_files = 0
            failed_files = 0

            def progress_callback(result, completed, total):
                nonlocal progress_task, successful_files, failed_files

                if progress_task is None:
                    progress_task = progress.add_task("Formatting files...", total=total)

                # Update counters
                if result.success:
                    successful_files += 1
                else:
                    failed_files += 1

                # Update progress description with current file and stats
                elapsed_time = time.time() - start_time
                rate = completed / elapsed_time if elapsed_time > 0 else 0

                description = f"Formatting files ({successful_files} ✓, {failed_files} ✗) | {rate:.1f} files/s"
                progress.update(progress_task, completed=completed, description=description)

                if verbose:
                    status = "✓" if result.success else "✗"
                    file_name = result.path.name
                    tool_info = f" ({result.tool_used})" if result.success else ""
                    if dry_run:
                        tool_info += " (preview)"
                    elif result.error_message:
                        tool_info = " (error)"
                    console.print(f"  {status} {file_name}{tool_info}")

            # Safety checks before processing
            target_path = Path(path)
            if not force and not dry_run:
                # Discover files first for safety analysis
                extensions = set(self.processor.tool_manager.format_commands.keys())
                files_to_process = self.processor.file_handler.find_files(
                    target_path, extensions, exclude_patterns, recursive, lazy_validation=True
                )

                if files_to_process:
                    from .safety import SafetyChecker, get_user_confirmation

                    safety_checker = SafetyChecker()
                    summary = safety_checker.get_operation_summary(
                        files_to_process, "format", dry_run
                    )

                    if not get_user_confirmation("format", summary):
                        console.print("Operation cancelled")
                        return

            result = self.processor.format_files(
                target_path,
                recursive=recursive,
                exclude_patterns=exclude_patterns,
                max_workers=self.config.get("max_workers", 4),
                create_backup=backup,
                dry_run=dry_run,
                progress_callback=progress_callback,
            )

        self._display_results(result, "formatting", verbose, dry_run)

    def tools(self):
        """Show available tools and their status."""

        tool_info = self.tool_manager.get_tool_info()

        # Create tools table
        table = Table()
        table.add_column("Tool", style="cyan", min_width=20)
        table.add_column("Status", style="bold", min_width=12)
        table.add_column("Type", style="blue", min_width=10)
        table.add_column("Language", style="yellow", min_width=10)
        table.add_column("Formats", style="green")

        # Sort tools: available first, then by speed (Rust/Go first)
        def sort_key(item):
            tool, info = item
            available = info["available"]
            is_fast = info["language"] in ["Rust", "Go"]
            return (not available, not is_fast, tool)

        for tool, info in sorted(tool_info.items(), key=sort_key):
            status = "[green]✓ Available[/green]" if info["available"] else "[red]✗ Missing[/red]"
            formats = (
                ", ".join(info["formats"]) if isinstance(info["formats"], list) else info["formats"]
            )

            table.add_row(tool, status, info["type"].title(), info["language"], formats)

        console.print(table)

        # Show summary
        available_count = sum(1 for info in tool_info.values() if info["available"])
        total_count = len(tool_info)
        fast_available = sum(
            1
            for info in tool_info.values()
            if info["available"] and info["language"] in ["Rust", "Go"]
        )

        console.print(f"\n{available_count}/{total_count} tools available")
        if fast_available > 0:
            console.print(f"{fast_available} fast tools (Rust/Go) available")

        if available_count < total_count:
            console.print("Install missing tools with 'vfor install'")

    def ignore(self, action: str = "init", path: str = "."):
        """
        Manage .vforignore files for gitignore-style exclusion patterns.

        Args:
            action: Action to perform (init, show, help)
            path: Directory path (default: current directory)
        """
        target_path = Path(path).resolve()

        if action == "init":
            console.print(
                Panel(
                    f"🚫 Creating .vforignore File\nPath: {target_path}",
                    title="VFor Ignore Setup",
                    style="bold cyan",
                )
            )

            if self.processor.file_handler.create_vforignore_file(target_path):
                console.print(
                    "[green]✓ Created .vforignore file with common exclusion patterns[/green]"
                )
                console.print(
                    f"[dim]Edit {target_path / '.vforignore'} to customize patterns[/dim]"
                )
            else:
                console.print("[red]✗ Failed to create .vforignore file[/red]")

        elif action == "show":
            console.print(
                Panel(
                    f"📋 Current Ignore Patterns\nPath: {target_path}",
                    title="VFor Ignore Status",
                    style="bold blue",
                )
            )

            # Load and display patterns
            patterns = self.processor.file_handler._load_gitignore_patterns(target_path)
            if patterns:
                console.print("[green]Active ignore patterns:[/green]")
                for pattern in patterns[:20]:  # Show first 20
                    console.print(f"  {pattern}")
                if len(patterns) > 20:
                    console.print(f"  [dim]... and {len(patterns) - 20} more[/dim]")
            else:
                console.print("[yellow]No ignore patterns found[/yellow]")
                console.print("[dim]Use 'vfor ignore init' to create a .vforignore file[/dim]")

        else:
            console.print("[bold]VFor Ignore File Management[/bold]")
            console.print("")
            console.print("[green]Commands:[/green]")
            console.print(
                "  vfor ignore init [path]  # Create .vforignore file with common patterns"
            )
            console.print("  vfor ignore show [path]  # Show current ignore patterns")
            console.print("  vfor ignore help         # Show this help message")
            console.print("")
            console.print("[blue]Gitignore-style Pattern Examples:[/blue]")
            console.print("  *.log                    # Ignore all .log files")
            console.print("  node_modules/            # Ignore node_modules directory")
            console.print("  build/**                 # Ignore everything in build directory")
            console.print("  !important.txt           # Don't ignore this specific file")
            console.print("  temp/                    # Ignore temp directory")
            console.print("  *.min.*                  # Ignore minified files")
            console.print("")
            console.print(
                "[dim]Files checked (in order): .gitignore, .vforignore, ../.gitignore, ~/.vforignore_global[/dim]"
            )

    def configure(self, action: str = "help"):
        """
        Manage vfor configuration.

        Args:
            action: Action to perform ('init', 'show', 'help')
        """
        if action == "init":
            config_path = Path(".vfor.json")
            if config_path.exists():
                console.print(f"[yellow]⚠ Config file already exists: {config_path}[/yellow]")
                console.print("[dim]Use --force to overwrite (not implemented)[/dim]")
                return

            try:
                create_example_config_file(config_path)
                console.print(f"[green]✓ Created example config file: {config_path}[/green]")
                console.print("[dim]Edit this file to customize vfor behavior[/dim]")
            except Exception as e:
                console.print(f"[red]✗ Failed to create config file: {e}[/red]")

        elif action == "show":
            console.print(
                Panel("Current VFor Configuration", title="⚙️ Configuration", style="bold cyan")
            )

            # Show current config values
            config_table = Table()
            config_table.add_column("Setting", style="cyan")
            config_table.add_column("Value", style="yellow")
            config_table.add_column("Source", style="dim")

            # Show key settings
            settings = [
                ("max_workers", self.config.get("max_workers")),
                ("preferred_js_tool", self.config.get("preferred_js_tool")),
                ("preferred_css_tool", self.config.get("preferred_css_tool")),
                ("preferred_python_tool", self.config.get("preferred_python_tool")),
                ("create_backup", self.config.get("create_backup")),
            ]

            for setting, value in settings:
                # Determine source (simplified)
                source = "default"
                if os.getenv(f"VFOR_{setting.upper()}"):
                    source = "environment"
                elif Path(".vfor.json").exists():
                    source = "config file"

                config_table.add_row(setting, str(value), source)

            console.print(config_table)

            # Show config file locations
            console.print("\n[bold]Config File Locations (in order of precedence):[/bold]")
            config_files = [
                Path.cwd() / ".vfor.json",
                Path.home() / ".vfor" / "config.json",
                Path("/etc/vfor/config.json"),
            ]

            for config_file in config_files:
                if config_file.exists():
                    console.print(f"  [green]✓[/green] {config_file}")
                else:
                    console.print(f"  [dim]✗ {config_file}[/dim]")

        else:
            console.print("Usage:")
            console.print("  vfor configure init   # Create example .vfor.json config file")
            console.print("  vfor configure show   # Show current configuration")
            console.print("  vfor configure help   # Show this help message")

    def cleanup(self, path: str = ".", *, recursive: bool = True):
        """
        Clean up backup files created by vfor.

        Args:
            path: Directory to clean (default: current directory)
            recursive: Clean recursively (default: True)
        """
        target_path = Path(path).resolve()

        console.print(
            Panel(
                f"🧹 Cleaning Backup Files\n"
                f"Path: {target_path}\n"
                f"Mode: {'Recursive' if recursive else 'Single level'}",
                title="Cleanup",
                style="bold yellow",
            )
        )

        cleaned = 0
        if recursive:
            for backup_pattern in ["**/*.vfor_backup", "**/*.vfor_temp"]:
                for backup_file in target_path.glob(backup_pattern):
                    try:
                        backup_file.unlink()
                        cleaned += 1
                    except Exception as e:
                        console.print(f"[red]Error removing {backup_file}: {e}[/red]")
        else:
            for backup_pattern in ["*.vfor_backup", "*.vfor_temp"]:
                for backup_file in target_path.glob(backup_pattern):
                    try:
                        backup_file.unlink()
                        cleaned += 1
                    except Exception as e:
                        console.print(f"[red]Error removing {backup_file}: {e}[/red]")

        if cleaned > 0:
            console.print(f"[green]✓ Removed {cleaned} backup files[/green]")
        else:
            console.print("[dim]No backup files found[/dim]")

    def install(self, verbose: bool = False):
        """
        Install all required formatting and minification tools.

        This command automatically installs:
        - Prerequisites (Homebrew, Node.js, Rust)
        - Universal tools (dprint, biome, esbuild)
        - Language-specific tools (ruff, jq, yq, taplo)
        - Performance tools (swc, terser, lightningcss, etc.)

        Args:
            verbose: Show detailed installation progress (default: False)
        """
        install_tools(verbose=verbose)

    def update(self, verbose: bool = False):
        """
        Update all installed tools to their latest versions.

        This command:
        - Updates package managers (brew, npm, rustup)
        - Updates all installed formatting/minification tools
        - Cleans up package manager caches
        - Verifies tool installations
        - Updates configuration files

        Args:
            verbose: Show detailed update progress (default: False)
        """
        update_tools(verbose=verbose)

    def benchmark(self, path: str = ".", operation: str = "both", verbose: bool = False):
        """
        Run performance benchmarks on file processing operations.

        Args:
            path: Directory or file path to benchmark (default: current directory)
            operation: Operation to benchmark - "minify", "format", or "both" (default: both)
            verbose: Show detailed benchmark results (default: False)
        """
        from rich.table import Table

        target_path = Path(path).resolve()

        console.print(
            Panel(
                f"⚡ Performance Benchmark\nPath: {target_path}\nOperation: {operation.title()}",
                title="VFor Benchmark",
                style="bold magenta",
            )
        )

        operations_to_run = []
        if operation in ["minify", "both"]:
            operations_to_run.append("minify")
        if operation in ["format", "both"]:
            operations_to_run.append("format")

        benchmark_results = []

        for op in operations_to_run:
            console.print(f"\n[bold]Running {op} benchmark...[/bold]")

            # Run the operation
            if op == "minify":
                result = self.processor.minify_files(
                    target_path,
                    recursive=True,
                    max_workers=self.config.get("max_workers", 4),
                    create_backup=False,
                    dry_run=True,  # Use dry-run to avoid modifying files
                )
            else:
                result = self.processor.format_files(
                    target_path,
                    recursive=True,
                    max_workers=self.config.get("max_workers", 4),
                    create_backup=False,
                    dry_run=True,  # Use dry-run to avoid modifying files
                )

            # Create benchmark analysis
            benchmark = self.processor.create_benchmark_result(result, op)
            benchmark_results.append(benchmark)

            # Display benchmark results
            self._display_benchmark_results(benchmark, verbose)

        # Summary comparison if both operations were run
        if len(benchmark_results) == 2:
            self._display_benchmark_comparison(benchmark_results)

    def _display_benchmark_results(self, benchmark, verbose: bool):
        """Display detailed benchmark results."""

        # Overall performance summary
        console.print(
            Panel(
                f"Files processed: {benchmark.total_files:,}\n"
                f"Total time: {benchmark.total_time:.3f}s\n"
                f"Average time per file: {benchmark.avg_time_per_file * 1000:.1f}ms\n"
                f"Processing speed: {benchmark.files_per_second:.1f} files/sec",
                title=f"📊 {benchmark.operation.title()} Performance Summary",
                style="bold blue",
            )
        )

        if verbose and benchmark.extension_stats:
            # Performance by file extension
            ext_table = Table(title="Performance by File Type")
            ext_table.add_column("Extension", style="cyan")
            ext_table.add_column("Count", justify="right")
            ext_table.add_column("Avg Time", justify="right")
            ext_table.add_column("Total Time", justify="right")
            ext_table.add_column("Avg Size", justify="right")

            for ext, stats in benchmark.extension_stats.items():
                ext_table.add_row(
                    ext,
                    str(stats["count"]),
                    f"{stats['avg_time'] * 1000:.1f}ms",
                    f"{stats['total_time']:.3f}s",
                    f"{stats['avg_size']:,.0f}B",
                )

            console.print(ext_table)

            # Tool usage statistics
            if benchmark.tools_used:
                tool_table = Table(title="Tools Used")
                tool_table.add_column("Tool", style="green")
                tool_table.add_column("Files Processed", justify="right")
                tool_table.add_column("Percentage", justify="right")

                for tool, count in sorted(
                    benchmark.tools_used.items(), key=lambda x: x[1], reverse=True
                ):
                    percentage = (count / benchmark.total_files) * 100
                    tool_table.add_row(tool, str(count), f"{percentage:.1f}%")

                console.print(tool_table)

    def _display_benchmark_comparison(self, benchmarks):
        """Display comparison between minify and format benchmarks."""
        minify_bench = next(b for b in benchmarks if b.operation == "minify")
        format_bench = next(b for b in benchmarks if b.operation == "format")

        comparison_table = Table(title="Operation Comparison")
        comparison_table.add_column("Metric")
        comparison_table.add_column("Minify", justify="right", style="blue")
        comparison_table.add_column("Format", justify="right", style="green")
        comparison_table.add_column("Faster", justify="center")

        # Compare processing speeds
        minify_speed = minify_bench.files_per_second
        format_speed = format_bench.files_per_second
        faster_op = "Minify" if minify_speed > format_speed else "Format"

        comparison_table.add_row(
            "Files/Second", f"{minify_speed:.1f}", f"{format_speed:.1f}", faster_op
        )

        comparison_table.add_row(
            "Avg Time/File",
            f"{minify_bench.avg_time_per_file * 1000:.1f}ms",
            f"{format_bench.avg_time_per_file * 1000:.1f}ms",
            "Minify"
            if minify_bench.avg_time_per_file < format_bench.avg_time_per_file
            else "Format",
        )

        comparison_table.add_row(
            "Total Time",
            f"{minify_bench.total_time:.3f}s",
            f"{format_bench.total_time:.3f}s",
            "Minify" if minify_bench.total_time < format_bench.total_time else "Format",
        )

        console.print(comparison_table)

    def perf_check(self, path: str = ".", operation: str = "both", create_baseline: bool = False):
        """
        Check for performance regressions against saved baselines.

        Args:
            path: Directory to benchmark (default: current directory)
            operation: Operation to check - "minify", "format", or "both" (default: both)
            create_baseline: Create new baseline instead of checking regression (default: False)
        """
        from .performance import PerformanceTracker, benchmark_with_regression_check

        target_path = Path(path).resolve()

        if not target_path.exists():
            console.print(f"[red]Error: Path does not exist: {target_path}[/red]")
            return

        console.print(
            Panel(
                f"Path: {target_path}\n"
                f"Operation: {operation}\n"
                f"Mode: {'Create Baseline' if create_baseline else 'Regression Check'}",
                title="🔍 Performance Regression Check",
                style="bold cyan",
            )
        )

        if create_baseline:
            tracker = PerformanceTracker()
            baselines = tracker.create_baseline_from_benchmark(target_path, operation)

            console.print(f"\n✅ Created {len(baselines)} performance baseline(s)")
            for baseline in baselines:
                console.print(
                    f"  • {baseline.operation}: {baseline.files_per_second:.1f} files/sec"
                )
        else:
            benchmark_with_regression_check(target_path, operation)

    def _display_results(self, result, operation_name: str, verbose: bool, dry_run: bool = False):
        """Display processing results."""

        # Quick summary line - no panel/frame
        if result.failed > 0:
            console.print(f"[red]Failed:[/red] {result.failed} files")

        if result.successful > 0:
            # Main success summary
            files_per_second = (
                result.total_files / result.total_time if result.total_time > 0 else 0
            )
            time_text = f"({result.total_time:.2f}s)" if verbose else ""

            # Add minification specific info
            if operation_name == "minification" and result.total_size_reduction != 0:
                size_reduction_text = f", {result.total_size_reduction_percent:+.1f}% size"
            else:
                size_reduction_text = ""

            preview_text = " (preview)" if dry_run else ""
            console.print(
                f"Processed {result.successful} files{size_reduction_text} {time_text}{preview_text}"
            )

        # Show error details only with verbose
        if result.failed > 0 and verbose:
            console.print("\nFailed files:")
            error_results = [r for r in result.results if not r.success and r.error_message]
            for error_result in error_results:
                console.print(f"  {error_result.path.name}: {error_result.error_message}")

        # Show successful files with verbose
        if verbose and result.successful > 0:
            console.print("\nSuccessful files:")
            successful_results = [r for r in result.results if r.success]
            for success_result in successful_results:
                if operation_name == "minification":
                    size_info = f" ({success_result.original_size:,} → {success_result.final_size:,} bytes, {success_result.size_reduction_percent:+.1f}%)"
                else:
                    size_info = f" ({success_result.processing_time:.3f}s)"
                console.print(f"  {success_result.path.name}{size_info}")


def main():
    """Main CLI entry point."""
    # Environment variable configuration
    max_workers = os.getenv("VFOR_MAX_WORKERS", "4")

    try:
        # Configure fire to use proper help formatting
        fire.Fire(VFor, serialize=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️  Operation cancelled by user[/yellow]")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"[red]✗ File not found: {e}[/red]")
        console.print("[yellow]💡 Check the path and try again[/yellow]")
        sys.exit(1)
    except PermissionError as e:
        from .files import FileHandler

        # Try to provide detailed permission analysis
        try:
            # Extract path from error if possible
            error_str = str(e)
            if "'" in error_str:
                path_str = error_str.split("'")[1]
                path = Path(path_str)
                file_handler = FileHandler()
                detailed_error = file_handler.diagnose_permission_error(path, "access")
                console.print(f"[red]✗ {detailed_error}[/red]")
            else:
                console.print(f"[red]✗ Permission denied: {e}[/red]")
                console.print(
                    "[yellow]💡 Try running with elevated privileges or check file permissions[/yellow]"
                )
        except Exception:
            # Fallback to simple error message
            console.print(f"[red]✗ Permission denied: {e}[/red]")
            console.print(
                "[yellow]💡 Check file permissions or run with appropriate privileges[/yellow]"
            )
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Unexpected error: {e}[/red]")
        console.print(
            "[dim]If this persists, please report it at: https://github.com/vexyart/vexy-formi/issues[/dim]"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
