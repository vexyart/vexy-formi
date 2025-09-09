#!/usr/bin/env python3
# this_file: src/vexy_formi/performance.py
"""
Performance regression detection for vexy-formi.

Simple baseline system to track performance metrics and detect regressions.
"""

import json
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .core import BenchmarkResult, FileProcessor


@dataclass
class PerformanceBaseline:
    """Performance baseline for regression detection."""

    timestamp: float
    version: str
    operation: str  # "minify" or "format"
    file_types: dict[str, float]  # extension -> avg_time_ms
    total_files: int
    avg_time_per_file: float  # ms
    files_per_second: float
    tools_used: dict[str, int]

    @classmethod
    def from_benchmark_result(
        cls, benchmark: BenchmarkResult, version: str = "1.0.3"
    ) -> "PerformanceBaseline":
        """Create baseline from benchmark result."""
        file_types = {}
        for ext, stats in benchmark.extension_stats.items():
            file_types[ext] = stats["avg_time"] * 1000  # Convert to ms

        return cls(
            timestamp=time.time(),
            version=version,
            operation=benchmark.operation,
            file_types=file_types,
            total_files=benchmark.total_files,
            avg_time_per_file=benchmark.avg_time_per_file * 1000,  # Convert to ms
            files_per_second=benchmark.files_per_second,
            tools_used=benchmark.tools_used,
        )


@dataclass
class RegressionReport:
    """Report of performance regression analysis."""

    has_regression: bool
    overall_change: float  # Percentage change in files_per_second
    threshold_exceeded: bool
    file_type_regressions: dict[str, float]  # extension -> percentage change
    summary: str
    details: list[str]


class PerformanceTracker:
    """Track and detect performance regressions."""

    def __init__(self, baseline_file: Path | None = None):
        self.baseline_file = (
            baseline_file or Path.home() / ".cache" / "vfor" / "performance_baselines.json"
        )
        self.baseline_file.parent.mkdir(parents=True, exist_ok=True)
        self.regression_threshold = 15.0  # 15% performance degradation threshold

    def save_baseline(self, baseline: PerformanceBaseline) -> None:
        """Save performance baseline to file."""
        baselines = self._load_baselines()

        # Keep only latest 10 baselines per operation
        operation_baselines = [b for b in baselines if b.operation == baseline.operation]
        if len(operation_baselines) >= 10:
            # Remove oldest
            operation_baselines.sort(key=lambda x: x.timestamp)
            baselines = [
                b
                for b in baselines
                if not (
                    b.operation == baseline.operation
                    and b.timestamp == operation_baselines[0].timestamp
                )
            ]

        baselines.append(baseline)
        self._save_baselines(baselines)

    def _load_baselines(self) -> list[PerformanceBaseline]:
        """Load baselines from file."""
        if not self.baseline_file.exists():
            return []

        try:
            with open(self.baseline_file) as f:
                data = json.load(f)
                return [PerformanceBaseline(**item) for item in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            return []

    def _save_baselines(self, baselines: list[PerformanceBaseline]) -> None:
        """Save baselines to file."""
        with open(self.baseline_file, "w") as f:
            json.dump([asdict(b) for b in baselines], f, indent=2)

    def check_regression(self, current: PerformanceBaseline) -> RegressionReport:
        """Check for performance regression against baseline."""
        baselines = self._load_baselines()

        # Find most recent baseline for same operation
        operation_baselines = [b for b in baselines if b.operation == current.operation]
        if not operation_baselines:
            return RegressionReport(
                has_regression=False,
                overall_change=0.0,
                threshold_exceeded=False,
                file_type_regressions={},
                summary="No baseline available for comparison",
                details=["This is the first baseline for this operation"],
            )

        # Use most recent baseline
        baseline = max(operation_baselines, key=lambda x: x.timestamp)

        # Calculate overall performance change
        overall_change = (
            (current.files_per_second - baseline.files_per_second) / baseline.files_per_second
        ) * 100

        # Check file type specific regressions
        file_type_regressions = {}
        for ext in current.file_types:
            if ext in baseline.file_types:
                baseline_time = baseline.file_types[ext]
                current_time = current.file_types[ext]
                # Positive change means slower (regression)
                change = ((current_time - baseline_time) / baseline_time) * 100
                if abs(change) > 5.0:  # Only report significant changes
                    file_type_regressions[ext] = change

        # Determine if regression occurred
        has_regression = overall_change < -self.regression_threshold
        threshold_exceeded = abs(overall_change) > self.regression_threshold

        # Create summary
        if has_regression:
            summary = f"⚠️  Performance regression detected: {abs(overall_change):.1f}% slower"
        elif overall_change > self.regression_threshold:
            summary = f"🚀 Performance improvement: {overall_change:.1f}% faster"
        else:
            summary = f"✅ Performance stable: {overall_change:+.1f}% change"

        # Create details
        details = [
            f"Baseline: {baseline.files_per_second:.1f} files/sec ({baseline.avg_time_per_file:.1f}ms/file)",
            f"Current:  {current.files_per_second:.1f} files/sec ({current.avg_time_per_file:.1f}ms/file)",
            f"Change:   {overall_change:+.1f}% ({'+' if overall_change > 0 else ''}{current.files_per_second - baseline.files_per_second:.1f} files/sec)",
        ]

        if file_type_regressions:
            details.append("File type changes:")
            for ext, change in file_type_regressions.items():
                status = "slower" if change > 0 else "faster"
                details.append(f"  {ext}: {abs(change):.1f}% {status}")

        return RegressionReport(
            has_regression=has_regression,
            overall_change=overall_change,
            threshold_exceeded=threshold_exceeded,
            file_type_regressions=file_type_regressions,
            summary=summary,
            details=details,
        )

    def create_baseline_from_benchmark(
        self, path: Path, operation: str = "both"
    ) -> list[PerformanceBaseline]:
        """Create performance baseline by running benchmark."""
        processor = FileProcessor()
        baselines = []

        operations = ["minify", "format"] if operation == "both" else [operation]

        for op in operations:
            # Run benchmark
            if op == "minify":
                result = processor.minify_files(
                    path, recursive=True, create_backup=False, dry_run=True
                )
            else:
                result = processor.format_files(
                    path, recursive=True, create_backup=False, dry_run=True
                )

            if result.total_files > 0:
                benchmark = processor.create_benchmark_result(result, op)
                baseline = PerformanceBaseline.from_benchmark_result(benchmark)
                baselines.append(baseline)
                self.save_baseline(baseline)

        return baselines


def benchmark_with_regression_check(path: Path, operation: str = "both") -> None:
    """Run benchmark and check for performance regressions."""
    tracker = PerformanceTracker()

    print("🔍 Creating performance baselines...")
    baselines = tracker.create_baseline_from_benchmark(path, operation)

    for baseline in baselines:
        print(f"\n📊 {baseline.operation.title()} Performance Analysis:")
        print(f"  Files processed: {baseline.total_files}")
        print(f"  Average time per file: {baseline.avg_time_per_file:.1f}ms")
        print(f"  Processing speed: {baseline.files_per_second:.1f} files/sec")

        # Check regression
        regression = tracker.check_regression(baseline)
        print(f"  {regression.summary}")

        if regression.threshold_exceeded:
            print("  Details:")
            for detail in regression.details:
                print(f"    {detail}")
