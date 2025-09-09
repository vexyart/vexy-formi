#!/usr/bin/env python3
# this_file: tests/test_performance.py
"""
Comprehensive tests for vexy-formi performance regression detection.

Tests the PerformanceTracker, baseline management, and regression detection
functionality.
"""

import os
import sys
import json
import tempfile
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src to path for testing
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from vexy_formi.performance import (
    PerformanceBaseline, 
    RegressionReport, 
    PerformanceTracker,
    benchmark_with_regression_check
)
from vexy_formi.core import BenchmarkResult


class TestPerformanceBaseline:
    """Test performance baseline functionality."""
    
    def test_baseline_creation(self):
        """Test creating a performance baseline."""
        baseline = PerformanceBaseline(
            timestamp=time.time(),
            version="1.0.4",
            operation="minify",
            file_types={".js": 15.0, ".css": 20.0},
            total_files=10,
            avg_time_per_file=17.5,
            files_per_second=57.1,
            tools_used={"esbuild": 5, "lightningcss": 2}
        )
        
        assert baseline.version == "1.0.4"
        assert baseline.operation == "minify"
        assert baseline.file_types[".js"] == 15.0
        assert baseline.total_files == 10
        assert baseline.avg_time_per_file == 17.5
        assert baseline.files_per_second == 57.1
    
    def test_baseline_from_benchmark_result(self):
        """Test creating baseline from benchmark result."""
        # Create a mock benchmark result
        benchmark = BenchmarkResult(
            operation="format",
            total_files=5,
            total_time=0.1,  # 100ms
            files_by_extension={".js": 3, ".py": 2},
            times_by_extension={".js": [0.02, 0.03, 0.025], ".py": [0.02, 0.023]},
            sizes_by_extension={".js": [1000, 1500, 1200], ".py": [800, 900]},
            tools_used={"biome": 3, "ruff": 2}
        )
        
        baseline = PerformanceBaseline.from_benchmark_result(benchmark, "1.0.4")
        
        assert baseline.version == "1.0.4"
        assert baseline.operation == "format"
        assert baseline.total_files == 5
        assert baseline.files_per_second == 50.0  # 5 files / 0.1 seconds
        assert baseline.avg_time_per_file == 20.0  # 0.02 * 1000 = 20ms
        assert baseline.tools_used == {"biome": 3, "ruff": 2}


class TestRegressionReport:
    """Test regression report functionality."""
    
    def test_regression_report_creation(self):
        """Test creating a regression report."""
        report = RegressionReport(
            has_regression=True,
            overall_change=-20.0,  # 20% slower
            threshold_exceeded=True,
            file_type_regressions={".js": 15.0, ".py": -5.0},
            summary="⚠️  Performance regression detected: 20.0% slower",
            details=["Performance degraded significantly"]
        )
        
        assert report.has_regression == True
        assert report.overall_change == -20.0
        assert report.threshold_exceeded == True
        assert ".js" in report.file_type_regressions
        assert report.file_type_regressions[".js"] == 15.0


class TestPerformanceTracker:
    """Test performance tracker functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.baseline_file = self.temp_dir / "test_baselines.json"
        self.tracker = PerformanceTracker(self.baseline_file)
    
    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_baseline(self, operation="minify", files_per_second=60.0, avg_time=16.7):
        """Create a test baseline."""
        return PerformanceBaseline(
            timestamp=time.time() - 3600,  # 1 hour ago
            version="1.0.3",
            operation=operation,
            file_types={".js": avg_time, ".css": avg_time * 1.2},
            total_files=10,
            avg_time_per_file=avg_time,
            files_per_second=files_per_second,
            tools_used={"esbuild": 6, "lightningcss": 4}
        )
    
    def test_save_and_load_baseline(self):
        """Test saving and loading baselines."""
        baseline = self.create_test_baseline()
        
        # Save baseline
        self.tracker.save_baseline(baseline)
        
        # Load baselines
        baselines = self.tracker._load_baselines()
        
        assert len(baselines) == 1
        assert baselines[0].operation == "minify"
        assert baselines[0].files_per_second == 60.0
        assert baselines[0].version == "1.0.3"
    
    def test_baseline_limit_enforcement(self):
        """Test that only latest 10 baselines are kept per operation."""
        # Add 12 baselines for the same operation
        for i in range(12):
            baseline = PerformanceBaseline(
                timestamp=time.time() + i,  # Increasing timestamp
                version=f"1.0.{i}",
                operation="minify",
                file_types={".js": 15.0},
                total_files=5,
                avg_time_per_file=15.0,
                files_per_second=66.7,
                tools_used={"esbuild": 5}
            )
            self.tracker.save_baseline(baseline)
        
        baselines = self.tracker._load_baselines()
        minify_baselines = [b for b in baselines if b.operation == "minify"]
        
        # Should only keep 10 latest baselines
        assert len(minify_baselines) == 10
        # Should have versions 1.0.2 through 1.0.11 (removed 1.0.0 and 1.0.1)
        versions = [b.version for b in minify_baselines]
        assert "1.0.0" not in versions
        assert "1.0.1" not in versions
        assert "1.0.11" in versions
    
    def test_no_regression_stable_performance(self):
        """Test regression detection with stable performance."""
        # Save a baseline
        baseline = self.create_test_baseline(files_per_second=60.0)
        self.tracker.save_baseline(baseline)
        
        # Create current performance (very similar)
        current = PerformanceBaseline(
            timestamp=time.time(),
            version="1.0.4",
            operation="minify",
            file_types={".js": 16.5, ".css": 20.0},  # Slightly different but within threshold
            total_files=10,
            avg_time_per_file=16.5,
            files_per_second=60.6,  # 1% improvement
            tools_used={"esbuild": 6, "lightningcss": 4}
        )
        
        report = self.tracker.check_regression(current)
        
        assert report.has_regression == False
        assert abs(report.overall_change) < 5.0  # Small change
        assert "Performance stable" in report.summary
    
    def test_performance_improvement_detection(self):
        """Test detection of performance improvements."""
        # Save a baseline
        baseline = self.create_test_baseline(files_per_second=50.0)
        self.tracker.save_baseline(baseline)
        
        # Create current performance (much better)
        current = PerformanceBaseline(
            timestamp=time.time(),
            version="1.0.4",
            operation="minify",
            file_types={".js": 12.0, ".css": 15.0},  # Faster processing
            total_files=10,
            avg_time_per_file=12.0,
            files_per_second=83.3,  # 66% improvement
            tools_used={"esbuild": 10}
        )
        
        report = self.tracker.check_regression(current)
        
        assert report.has_regression == False
        assert report.overall_change > 15.0  # Significant improvement
        assert report.threshold_exceeded == True  # Above improvement threshold
        assert "Performance improvement" in report.summary
    
    def test_performance_regression_detection(self):
        """Test detection of performance regressions."""
        # Save a baseline with good performance
        baseline = self.create_test_baseline(files_per_second=80.0, avg_time=12.5)
        self.tracker.save_baseline(baseline)
        
        # Create current performance (much worse)
        current = PerformanceBaseline(
            timestamp=time.time(),
            version="1.0.4",
            operation="minify",
            file_types={".js": 25.0, ".css": 30.0},  # Slower processing
            total_files=10,
            avg_time_per_file=25.0,
            files_per_second=40.0,  # 50% slower
            tools_used={"esbuild": 10}
        )
        
        report = self.tracker.check_regression(current)
        
        assert report.has_regression == True
        assert report.overall_change < -15.0  # Significant degradation
        assert report.threshold_exceeded == True
        assert "Performance regression detected" in report.summary
        assert "slower" in report.summary.lower()
    
    def test_file_type_specific_regression(self):
        """Test detection of file type specific regressions."""
        # Save baseline
        baseline = PerformanceBaseline(
            timestamp=time.time() - 3600,
            version="1.0.3",
            operation="format",
            file_types={".js": 10.0, ".py": 15.0, ".css": 12.0},
            total_files=15,
            avg_time_per_file=12.3,
            files_per_second=81.3,
            tools_used={"biome": 10, "ruff": 5}
        )
        self.tracker.save_baseline(baseline)
        
        # Create current with specific file type regression
        current = PerformanceBaseline(
            timestamp=time.time(),
            version="1.0.4",
            operation="format",
            file_types={".js": 20.0, ".py": 16.0, ".css": 12.0},  # JS much slower
            total_files=15,
            avg_time_per_file=16.0,
            files_per_second=62.5,
            tools_used={"biome": 10, "ruff": 5}
        )
        
        report = self.tracker.check_regression(current)
        
        # Should detect regression in JS files specifically
        assert ".js" in report.file_type_regressions
        js_change = report.file_type_regressions[".js"]
        assert js_change > 50  # JS files are 100% slower (doubled time)
    
    def test_no_baseline_available(self):
        """Test regression check with no baseline available."""
        current = self.create_test_baseline("format")
        
        report = self.tracker.check_regression(current)
        
        assert report.has_regression == False
        assert "No baseline available" in report.summary
        assert "first baseline" in report.details[0]
    
    def test_corrupted_baseline_file_handling(self):
        """Test handling of corrupted baseline files."""
        # Create a corrupted JSON file
        self.baseline_file.write_text("{ invalid json content")
        
        # Should gracefully handle corruption and return empty list
        baselines = self.tracker._load_baselines()
        assert len(baselines) == 0
        
        # Should still be able to save new baselines
        new_baseline = self.create_test_baseline()
        self.tracker.save_baseline(new_baseline)
        
        # Should now have one baseline
        baselines = self.tracker._load_baselines()
        assert len(baselines) == 1


class TestBenchmarkWithRegressionCheck:
    """Test the integrated benchmark with regression checking."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        # Create some test files
        (self.temp_dir / "test1.js").write_text("console.log('test');")
        (self.temp_dir / "test2.py").write_text("print('test')")
    
    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @patch('vexy_formi.performance.PerformanceTracker')
    def test_benchmark_integration(self, mock_tracker_class):
        """Test integrated benchmarking with regression checking."""
        # Mock the tracker instance
        mock_tracker = MagicMock()
        mock_tracker_class.return_value = mock_tracker
        
        # Mock baselines creation
        mock_baselines = [
            PerformanceBaseline(
                timestamp=time.time(),
                version="1.0.4",
                operation="minify",
                file_types={".js": 15.0},
                total_files=1,
                avg_time_per_file=15.0,
                files_per_second=66.7,
                tools_used={"esbuild": 1}
            )
        ]
        mock_tracker.create_baseline_from_benchmark.return_value = mock_baselines
        
        # Mock regression check
        mock_regression = RegressionReport(
            has_regression=False,
            overall_change=2.0,
            threshold_exceeded=False,
            file_type_regressions={},
            summary="✅ Performance stable: +2.0% change",
            details=["Performance is stable"]
        )
        mock_tracker.check_regression.return_value = mock_regression
        
        # Redirect stdout to capture print output
        from io import StringIO
        import sys
        captured_output = StringIO()
        
        # Test the function (would normally print to console)
        with patch('sys.stdout', captured_output):
            benchmark_with_regression_check(self.temp_dir, "minify")
        
        output = captured_output.getvalue()
        
        # Verify tracker was called correctly
        mock_tracker.create_baseline_from_benchmark.assert_called_once_with(self.temp_dir, "minify")
        mock_tracker.check_regression.assert_called_once()
        
        # Verify output contains expected content
        assert "Performance Analysis" in output
        assert "Performance stable" in output


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])