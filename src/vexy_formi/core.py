#!/usr/bin/env python3
# this_file: src/vexy_formi/core.py
"""
Core processing logic for vexy-formi.

Simplified minification and formatting operations focused on speed and reliability.
Removes enterprise monitoring and complex error recovery while preserving
essential functionality and basic safety.
"""

import statistics
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from .config import Config
from .files import FileHandler
from .tools import ToolManager


@dataclass
class ProcessResult:
    """Result of processing a single file."""

    path: Path
    success: bool
    original_size: int
    final_size: int
    tool_used: str
    processing_time: float = 0.0
    error_message: str | None = None

    @property
    def size_reduction_percent(self) -> float:
        """Calculate percentage reduction in file size."""
        if self.original_size == 0:
            return 0.0
        return ((self.original_size - self.final_size) / self.original_size) * 100

    @property
    def size_change(self) -> int:
        """Calculate size change in bytes."""
        return self.final_size - self.original_size


@dataclass
class BatchResult:
    """Result of batch processing operation."""

    total_files: int
    successful: int
    failed: int
    total_time: float
    total_size_before: int
    total_size_after: int
    results: list[ProcessResult]

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.successful / self.total_files) * 100

    @property
    def total_size_reduction(self) -> int:
        """Calculate total size reduction in bytes."""
        return self.total_size_before - self.total_size_after

    @property
    def total_size_reduction_percent(self) -> float:
        """Calculate total percentage size reduction."""
        if self.total_size_before == 0:
            return 0.0
        return ((self.total_size_before - self.total_size_after) / self.total_size_before) * 100


@dataclass
class BenchmarkResult:
    """Result of performance benchmarking operations."""

    operation: str  # "minify" or "format"
    total_files: int
    total_time: float
    files_by_extension: dict[str, int]  # {'.js': 5, '.py': 3}
    times_by_extension: dict[str, list[float]]  # {'.js': [0.1, 0.2], '.py': [0.5]}
    sizes_by_extension: dict[str, list[int]]  # {'.js': [1000, 2000], '.py': [500]}
    tools_used: dict[str, int]  # {'esbuild': 5, 'ruff': 3}

    @property
    def avg_time_per_file(self) -> float:
        """Calculate average processing time per file."""
        return self.total_time / self.total_files if self.total_files > 0 else 0.0

    @property
    def files_per_second(self) -> float:
        """Calculate processing speed in files per second."""
        return self.total_files / self.total_time if self.total_time > 0 else 0.0

    @property
    def extension_stats(self) -> dict[str, dict[str, float]]:
        """Calculate statistics by file extension."""
        stats = {}
        for ext in self.files_by_extension:
            times = self.times_by_extension.get(ext, [])
            sizes = self.sizes_by_extension.get(ext, [])

            if times:
                stats[ext] = {
                    "count": self.files_by_extension[ext],
                    "avg_time": statistics.mean(times),
                    "median_time": statistics.median(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "avg_size": statistics.mean(sizes) if sizes else 0,
                    "total_time": sum(times),
                }
        return stats


class FileProcessor:
    """Core file processing engine."""

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.tool_manager = ToolManager(self.config)
        self.file_handler = FileHandler()

    def minify_file(
        self, file_path: Path, create_backup: bool = True, dry_run: bool = False
    ) -> ProcessResult:
        """
        Minify a single file.

        Args:
            file_path: Path to file to minify
            create_backup: Whether to create backup before processing
            dry_run: Preview changes without modifying files

        Returns:
            ProcessResult with operation details
        """
        start_time = time.time()

        # Basic validation
        is_valid, error_msg = self.file_handler.validate_file(file_path)
        if not is_valid:
            return ProcessResult(
                path=file_path,
                success=False,
                original_size=0,
                final_size=0,
                tool_used="validation",
                processing_time=time.time() - start_time,
                error_message=error_msg,
            )

        # Check if we support this file type
        if not self.tool_manager.supports_minify(file_path):
            return ProcessResult(
                path=file_path,
                success=False,
                original_size=file_path.stat().st_size,
                final_size=file_path.stat().st_size,
                tool_used="unsupported",
                processing_time=time.time() - start_time,
                error_message=f"No minification tool available for {file_path.suffix}",
            )

        original_size = file_path.stat().st_size

        # Try processing with graceful degradation (fallback to other tools if primary fails)
        return self._process_file_with_fallback(
            file_path, "minify", original_size, start_time, create_backup, dry_run
        )

    def format_file(
        self, file_path: Path, create_backup: bool = True, dry_run: bool = False
    ) -> ProcessResult:
        """
        Format a single file.

        Args:
            file_path: Path to file to format
            create_backup: Whether to create backup before processing
            dry_run: Preview changes without modifying files

        Returns:
            ProcessResult with operation details
        """
        start_time = time.time()

        # Basic validation
        is_valid, error_msg = self.file_handler.validate_file(file_path)
        if not is_valid:
            return ProcessResult(
                path=file_path,
                success=False,
                original_size=0,
                final_size=0,
                tool_used="validation",
                processing_time=time.time() - start_time,
                error_message=error_msg,
            )

        # Check if we support this file type
        if not self.tool_manager.supports_format(file_path):
            return ProcessResult(
                path=file_path,
                success=False,
                original_size=file_path.stat().st_size,
                final_size=file_path.stat().st_size,
                tool_used="unsupported",
                processing_time=time.time() - start_time,
                error_message=f"No formatting tool available for {file_path.suffix}",
            )

        original_size = file_path.stat().st_size

        # Try processing with graceful degradation (fallback to other tools if primary fails)
        return self._process_file_with_fallback(
            file_path, "format", original_size, start_time, create_backup, dry_run
        )

    def _process_file_with_tool(
        self,
        file_path: Path,
        tool_name: str,
        command_template: list[str],
        original_size: int,
        start_time: float,
        create_backup: bool,
    ) -> ProcessResult:
        """Execute tool command on file with atomic operations."""

        # Handle in-place tools (many formatters)
        if self._is_inplace_tool(tool_name, command_template):
            return self._process_inplace(
                file_path, tool_name, command_template, original_size, start_time, create_backup
            )

        # Handle tools that output to separate file
        return self._process_with_output(
            file_path, tool_name, command_template, original_size, start_time, create_backup
        )

    def _process_file_with_fallback(
        self,
        file_path: Path,
        operation: str,
        original_size: int,
        start_time: float,
        create_backup: bool,
        dry_run: bool = False,
    ) -> ProcessResult:
        """Process file with automatic tool fallback for graceful degradation."""

        if dry_run:
            # In dry-run mode, simulate processing without modifying files
            return self._simulate_processing(file_path, operation, original_size, start_time)

        # Try to execute with fallback to other tools
        success, error_msg, tool_used = self.tool_manager.execute_command_with_fallback(
            file_path, operation
        )

        processing_time = time.time() - start_time

        if success and tool_used:
            final_size = file_path.stat().st_size
            return ProcessResult(
                path=file_path,
                success=True,
                original_size=original_size,
                final_size=final_size,
                tool_used=tool_used,
                processing_time=processing_time,
            )
        return ProcessResult(
            path=file_path,
            success=False,
            original_size=original_size,
            final_size=original_size,
            tool_used=tool_used or "no_tool",
            processing_time=processing_time,
            error_message=error_msg,
        )

    def _simulate_processing(
        self, file_path: Path, operation: str, original_size: int, start_time: float
    ) -> ProcessResult:
        """Simulate file processing for dry-run mode."""

        # Find the tool that would be used
        if operation == "minify":
            commands = self.tool_manager.get_minify_command_with_fallback(file_path)
        else:
            commands = self.tool_manager.get_format_command_with_fallback(file_path)

        if not commands:
            return ProcessResult(
                path=file_path,
                success=False,
                original_size=original_size,
                final_size=original_size,
                tool_used="no_tool",
                processing_time=time.time() - start_time,
                error_message=f"No {operation} tools available for {file_path.suffix}",
            )

        # Use the first available tool for simulation
        tool_used, _ = commands[0]

        # For dry-run, estimate potential size savings based on operation and file type
        estimated_final_size = self._estimate_processed_size(file_path, operation, original_size)

        return ProcessResult(
            path=file_path,
            success=True,
            original_size=original_size,
            final_size=estimated_final_size,
            tool_used=f"{tool_used} (dry-run)",
            processing_time=time.time() - start_time,
            error_message=None,
        )

    def _estimate_processed_size(self, file_path: Path, operation: str, original_size: int) -> int:
        """Estimate file size after processing for dry-run mode."""
        ext = file_path.suffix.lower()

        if operation == "minify":
            # Conservative estimates for minification based on file type
            minify_estimates = {
                ".js": 0.65,  # ~35% reduction typical for JS
                ".css": 0.70,  # ~30% reduction typical for CSS
                ".html": 0.75,  # ~25% reduction typical for HTML
                ".json": 0.80,  # ~20% reduction typical for JSON
            }
            reduction_factor = minify_estimates.get(ext, 0.90)  # Default 10% reduction
        else:
            # Formatting typically increases size slightly due to consistent spacing
            format_estimates = {
                ".py": 1.05,  # Python formatting might add some whitespace
                ".js": 1.02,  # JS formatting usually minimal change
                ".ts": 1.02,  # TS formatting usually minimal change
                ".css": 1.03,  # CSS formatting might add some spacing
                ".json": 1.10,  # JSON formatting adds indentation
                ".html": 1.05,  # HTML formatting adds structure
            }
            reduction_factor = format_estimates.get(ext, 1.0)  # Default no change

        return int(original_size * reduction_factor)

    def _is_inplace_tool(self, tool_name: str, command_template: list[str]) -> bool:
        """Check if tool modifies files in-place."""
        # Tools that typically work in-place
        inplace_tools = {"ruff", "black", "biome", "prettier", "dprint", "taplo"}
        if tool_name in inplace_tools:
            return True

        # Check if command template has no output placeholder
        return "{output}" not in " ".join(command_template)

    def _process_inplace(
        self,
        file_path: Path,
        tool_name: str,
        command_template: list[str],
        original_size: int,
        start_time: float,
        create_backup: bool,
    ) -> ProcessResult:
        """Process file with in-place tool."""

        # Execute the command
        success, error_msg = self.tool_manager.execute_command(
            tool_name, command_template, file_path, None
        )

        processing_time = time.time() - start_time

        if success:
            final_size = file_path.stat().st_size
            return ProcessResult(
                path=file_path,
                success=True,
                original_size=original_size,
                final_size=final_size,
                tool_used=tool_name,
                processing_time=processing_time,
            )
        return ProcessResult(
            path=file_path,
            success=False,
            original_size=original_size,
            final_size=original_size,
            tool_used=tool_name,
            processing_time=processing_time,
            error_message=error_msg,
        )

    def _process_with_output(
        self,
        file_path: Path,
        tool_name: str,
        command_template: list[str],
        original_size: int,
        start_time: float,
        create_backup: bool,
    ) -> ProcessResult:
        """Process file with tool that outputs to separate file."""

        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix=file_path.suffix, delete=False) as temp_file:
            temp_path = Path(temp_file.name)

        try:
            # Execute command with temporary output
            success, error_msg = self.tool_manager.execute_command(
                tool_name, command_template, file_path, temp_path
            )

            processing_time = time.time() - start_time

            if success and temp_path.exists() and temp_path.stat().st_size > 0:
                # Read processed content
                with open(temp_path, "rb") as f:
                    processed_content = f.read()

                # Write back atomically
                if self.file_handler.atomic_write(file_path, processed_content, create_backup):
                    final_size = len(processed_content)
                    return ProcessResult(
                        path=file_path,
                        success=True,
                        original_size=original_size,
                        final_size=final_size,
                        tool_used=tool_name,
                        processing_time=processing_time,
                    )
                return ProcessResult(
                    path=file_path,
                    success=False,
                    original_size=original_size,
                    final_size=original_size,
                    tool_used=tool_name,
                    processing_time=processing_time,
                    error_message="Failed to write processed content",
                )
            return ProcessResult(
                path=file_path,
                success=False,
                original_size=original_size,
                final_size=original_size,
                tool_used=tool_name,
                processing_time=processing_time,
                error_message=error_msg or "Tool produced no output",
            )

        finally:
            # Clean up temporary file
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass

    def minify_files(
        self,
        paths: Path | list[Path],
        recursive: bool = True,
        exclude_patterns: list[str] | None = None,
        max_workers: int = 4,
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Callable[[ProcessResult, int, int], None] | None = None,
    ) -> BatchResult:
        """
        Minify multiple files.

        Args:
            paths: Single path or list of paths to process
            recursive: Whether to process directories recursively
            exclude_patterns: Patterns to exclude
            max_workers: Number of parallel workers
            create_backup: Whether to create backups
            dry_run: Preview changes without modifying files
            progress_callback: Optional callback for progress updates (result, completed, total)

        Returns:
            BatchResult with overall statistics
        """
        return self._batch_process(
            paths,
            "minify",
            recursive,
            exclude_patterns,
            max_workers,
            create_backup,
            dry_run,
            progress_callback,
        )

    def format_files(
        self,
        paths: Path | list[Path],
        recursive: bool = True,
        exclude_patterns: list[str] | None = None,
        max_workers: int = 4,
        create_backup: bool = True,
        dry_run: bool = False,
        progress_callback: Callable[[ProcessResult, int, int], None] | None = None,
    ) -> BatchResult:
        """
        Format multiple files.

        Args:
            paths: Single path or list of paths to process
            recursive: Whether to process directories recursively
            exclude_patterns: Patterns to exclude
            max_workers: Number of parallel workers
            create_backup: Whether to create backups
            dry_run: Preview changes without modifying files
            progress_callback: Optional callback for progress updates (result, completed, total)

        Returns:
            BatchResult with overall statistics
        """
        return self._batch_process(
            paths,
            "format",
            recursive,
            exclude_patterns,
            max_workers,
            create_backup,
            dry_run,
            progress_callback,
        )

    def _batch_process(
        self,
        paths: Path | list[Path],
        operation: str,
        recursive: bool,
        exclude_patterns: list[str] | None,
        max_workers: int,
        create_backup: bool,
        dry_run: bool = False,
        progress_callback: Callable[[ProcessResult, int, int], None] | None = None,
    ) -> BatchResult:
        """Internal batch processing logic."""

        start_time = time.time()

        # Normalize paths to list
        if isinstance(paths, Path):
            paths = [paths]

        # Find all files to process
        all_files = []
        for path in paths:
            if path.is_file():
                all_files.append(path)
            elif path.is_dir():
                # Get supported extensions based on operation
                if operation == "minify":
                    extensions = set(self.tool_manager.minify_commands.keys())
                else:
                    extensions = set(self.tool_manager.format_commands.keys())

                # Use lazy validation for better performance on large directories
                files = self.file_handler.find_files(
                    path, extensions, exclude_patterns, recursive, lazy_validation=True
                )
                all_files.extend(files)

        if not all_files:
            return BatchResult(
                total_files=0,
                successful=0,
                failed=0,
                total_time=time.time() - start_time,
                total_size_before=0,
                total_size_after=0,
                results=[],
            )

        # Process files in parallel
        results = []
        total_size_before = sum(f.stat().st_size for f in all_files if f.exists())

        process_func = self.minify_file if operation == "minify" else self.format_file

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all jobs
            future_to_file = {
                executor.submit(process_func, file_path, create_backup, dry_run): file_path
                for file_path in all_files
            }

            # Collect results with progress reporting
            for future in as_completed(future_to_file):
                result = future.result()
                results.append(result)

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(result, len(results), len(all_files))

        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_size_after = sum(r.final_size for r in results)
        total_time = time.time() - start_time

        return BatchResult(
            total_files=len(all_files),
            successful=successful,
            failed=failed,
            total_time=total_time,
            total_size_before=total_size_before,
            total_size_after=total_size_after,
            results=results,
        )

    def create_benchmark_result(self, batch_result: BatchResult, operation: str) -> BenchmarkResult:
        """
        Create detailed benchmarking analysis from batch processing results.

        Args:
            batch_result: Result from batch processing operation
            operation: Type of operation ("minify" or "format")

        Returns:
            BenchmarkResult with detailed performance analysis
        """
        files_by_extension = {}
        times_by_extension = {}
        sizes_by_extension = {}
        tools_used = {}

        for result in batch_result.results:
            ext = result.path.suffix.lower() or ".unknown"

            # Count files by extension
            files_by_extension[ext] = files_by_extension.get(ext, 0) + 1

            # Collect times by extension
            if ext not in times_by_extension:
                times_by_extension[ext] = []
            times_by_extension[ext].append(result.processing_time)

            # Collect sizes by extension
            if ext not in sizes_by_extension:
                sizes_by_extension[ext] = []
            sizes_by_extension[ext].append(result.original_size)

            # Count tools used
            tool_name = result.tool_used.replace(" (dry-run)", "")  # Remove dry-run suffix
            tools_used[tool_name] = tools_used.get(tool_name, 0) + 1

        return BenchmarkResult(
            operation=operation,
            total_files=batch_result.total_files,
            total_time=batch_result.total_time,
            files_by_extension=files_by_extension,
            times_by_extension=times_by_extension,
            sizes_by_extension=sizes_by_extension,
            tools_used=tools_used,
        )


# Convenience functions for API
def minify_files(path: str | Path | list[str | Path], **kwargs) -> dict[str, any]:
    """
    Minify files at the given path(s).

    Args:
        path: File or directory path(s) to minify
        **kwargs: Additional arguments (recursive, exclude, max_workers, etc.)

    Returns:
        Dictionary with results
    """
    processor = FileProcessor()

    # Convert string paths to Path objects
    if isinstance(path, str):
        path = Path(path)
    elif isinstance(path, list):
        path = [Path(p) if isinstance(p, str) else p for p in path]

    result = processor.minify_files(path, **kwargs)

    return {
        "success": result.successful > 0,
        "total_files": result.total_files,
        "successful": result.successful,
        "failed": result.failed,
        "total_time": result.total_time,
        "size_reduction_bytes": result.total_size_reduction,
        "size_reduction_percent": result.total_size_reduction_percent,
        "errors": [r.error_message for r in result.results if r.error_message],
    }


def format_files(path: str | Path | list[str | Path], **kwargs) -> dict[str, any]:
    """
    Format files at the given path(s).

    Args:
        path: File or directory path(s) to format
        **kwargs: Additional arguments (recursive, exclude, max_workers, etc.)

    Returns:
        Dictionary with results
    """
    processor = FileProcessor()

    # Convert string paths to Path objects
    if isinstance(path, str):
        path = Path(path)
    elif isinstance(path, list):
        path = [Path(p) if isinstance(p, str) else p for p in path]

    result = processor.format_files(path, **kwargs)

    return {
        "success": result.successful > 0,
        "total_files": result.total_files,
        "successful": result.successful,
        "failed": result.failed,
        "total_time": result.total_time,
        "errors": [r.error_message for r in result.results if r.error_message],
    }
