#!/usr/bin/env python3
# this_file: src/vexy_formi/safety.py
"""
Safety checks and user protection for vexy-formi operations.

Implements warnings, confirmations, and safety thresholds to protect users
from potentially destructive operations on large codebases.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class SafetyThresholds:
    """Safety thresholds for operation warnings."""

    # File count thresholds
    warn_file_count: int = 100  # Warn above 100 files
    critical_file_count: int = 1000  # Critical above 1000 files

    # Total size thresholds (in bytes)
    warn_total_size: int = 50 * 1024 * 1024  # Warn above 50MB
    critical_total_size: int = 500 * 1024 * 1024  # Critical above 500MB

    # Individual file size thresholds
    warn_large_file: int = 5 * 1024 * 1024  # Warn for files > 5MB
    critical_large_file: int = 50 * 1024 * 1024  # Critical for files > 50MB


@dataclass
class SafetyReport:
    """Safety analysis report for an operation."""

    operation: str  # "minify" or "format"
    total_files: int
    total_size: int
    large_files: list[tuple[Path, int]]  # (path, size) for large files

    # Risk levels
    is_safe: bool
    risk_level: str  # "low", "medium", "high", "critical"
    warnings: list[str]
    recommendations: list[str]

    @property
    def total_size_mb(self) -> float:
        """Total size in MB."""
        return self.total_size / (1024 * 1024)

    @property
    def requires_confirmation(self) -> bool:
        """Whether operation requires user confirmation."""
        return self.risk_level in ("high", "critical")


class SafetyChecker:
    """Safety checker for file operations."""

    def __init__(self, thresholds: SafetyThresholds | None = None):
        self.thresholds = thresholds or SafetyThresholds()

    def analyze_operation(self, files: list[Path], operation: str) -> SafetyReport:
        """
        Analyze an operation for safety concerns.

        Args:
            files: List of files to be processed
            operation: Type of operation ("minify" or "format")

        Returns:
            SafetyReport with analysis and recommendations
        """
        total_files = len(files)
        total_size = 0
        large_files = []
        warnings = []
        recommendations = []

        # Analyze files
        for file_path in files:
            try:
                size = file_path.stat().st_size
                total_size += size

                # Check for large individual files
                if size >= self.thresholds.critical_large_file or size >= self.thresholds.warn_large_file:
                    large_files.append((file_path, size))

            except (OSError, FileNotFoundError):
                # Skip files we can't access
                continue

        # Determine risk level and generate warnings
        risk_level = "low"
        is_safe = True

        # Check file count thresholds
        if total_files >= self.thresholds.critical_file_count:
            risk_level = "critical"
            is_safe = False
            warnings.append(f"⚠️  Very large operation: {total_files:,} files")
            recommendations.append("Consider processing in smaller batches")
        elif total_files >= self.thresholds.warn_file_count:
            risk_level = "high" if risk_level == "low" else risk_level
            warnings.append(f"🔶 Large operation: {total_files:,} files")
            recommendations.append("Double-check that all files should be processed")

        # Check total size thresholds
        if total_size >= self.thresholds.critical_total_size:
            risk_level = "critical"
            is_safe = False
            warnings.append(f"⚠️  Very large total size: {total_size / (1024 * 1024 * 1024):.1f}GB")
            recommendations.append("Ensure sufficient disk space for backups")
        elif total_size >= self.thresholds.warn_total_size:
            risk_level = "high" if risk_level == "low" else risk_level
            warnings.append(f"🔶 Large total size: {total_size / (1024 * 1024):.1f}MB")

        # Check for individual large files
        critical_large_files = [
            f for f in large_files if f[1] >= self.thresholds.critical_large_file
        ]
        warn_large_files = [
            f
            for f in large_files
            if f[1] >= self.thresholds.warn_large_file
            and f[1] < self.thresholds.critical_large_file
        ]

        if critical_large_files:
            risk_level = "critical"
            is_safe = False
            warnings.append(f"⚠️  {len(critical_large_files)} very large files (>50MB)")
            recommendations.append("Large files may take significant time to process")

        if warn_large_files:
            warnings.append(f"🔶 {len(warn_large_files)} large files (>5MB)")

        # Operation-specific warnings
        if operation == "minify" and total_files > 50:
            recommendations.append(
                "Minification creates backup files - ensure sufficient disk space"
            )

        if operation == "format" and any(f[1] > 10 * 1024 * 1024 for f in large_files):
            recommendations.append(
                "Formatting large files may significantly increase processing time"
            )

        # Add general safety recommendations
        if risk_level in ("high", "critical"):
            recommendations.append("Review file list with --dry-run first")
            recommendations.append("Ensure you have recent backups")

        return SafetyReport(
            operation=operation,
            total_files=total_files,
            total_size=total_size,
            large_files=large_files,
            is_safe=is_safe,
            risk_level=risk_level,
            warnings=warnings,
            recommendations=recommendations,
        )

    def format_safety_summary(self, report: SafetyReport) -> str:
        """Format a safety summary for display."""
        lines = []

        # Basic stats
        lines.append(f"Files: {report.total_files:,}")
        lines.append(f"Total size: {report.total_size_mb:.1f}MB")
        lines.append(f"Risk level: {report.risk_level.upper()}")

        # Large files summary
        if report.large_files:
            large_count = len(report.large_files)
            largest_size = max(f[1] for f in report.large_files) / (1024 * 1024)
            lines.append(f"Large files: {large_count} (largest: {largest_size:.1f}MB)")

        return " | ".join(lines)

    def should_warn_about_git_repo(self, path: Path) -> tuple[bool, str]:
        """Check if operation might affect a git repository."""
        # Look for .git directory in path or parents
        current = path.resolve()
        while current.parent != current:
            if (current / ".git").exists():
                # Check if we're processing the entire repo
                if path.resolve() == current:
                    return True, f"⚠️  Processing entire git repository: {current}"
                return False, ""
            current = current.parent
        return False, ""

    def get_operation_summary(
        self, files: list[Path], operation: str, dry_run: bool = False
    ) -> dict:
        """Get comprehensive operation summary."""
        report = self.analyze_operation(files, operation)

        # Check for git repository
        is_git_repo = False
        git_warning = ""
        if files:
            # Check the parent directory of the first file
            parent_dir = files[0].parent if files[0].is_file() else files[0]
            is_git_repo, git_warning = self.should_warn_about_git_repo(parent_dir)

        return {
            "safety_report": report,
            "is_git_repo": is_git_repo,
            "git_warning": git_warning,
            "dry_run": dry_run,
            "summary": self.format_safety_summary(report),
        }


def get_user_confirmation(operation: str, summary: dict) -> bool:
    """
    Get user confirmation for potentially risky operations.

    Args:
        operation: Operation name ("minify" or "format")
        summary: Operation summary from get_operation_summary()

    Returns:
        True if user confirms, False otherwise
    """
    report = summary["safety_report"]

    if not report.requires_confirmation:
        return True

    print(f"\n🔍 {operation.title()} Operation Summary:")
    print(f"   {summary['summary']}")

    if summary["git_warning"]:
        print(f"   {summary['git_warning']}")

    if report.warnings:
        print("\n⚠️  Warnings:")
        for warning in report.warnings:
            print(f"   {warning}")

    if report.recommendations:
        print("\n💡 Recommendations:")
        for rec in report.recommendations:
            print(f"   • {rec}")

    print(f"\n🚨 This is a {report.risk_level.upper()} risk operation.")

    # Get user confirmation
    try:
        response = input("\nDo you want to continue? [y/N]: ").strip().lower()
        return response in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print("\n❌ Operation cancelled by user")
        return False
