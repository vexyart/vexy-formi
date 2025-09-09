#!/usr/bin/env python3
# this_file: tests/test_safety.py
"""
Comprehensive tests for vexy-formi safety system.

Tests the SafetyChecker, safety thresholds, risk assessment,
and user protection mechanisms.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO

# Add src to path for testing
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from vexy_formi.safety import SafetyChecker, SafetyThresholds, SafetyReport, get_user_confirmation


class TestSafetyThresholds:
    """Test safety threshold configuration."""
    
    def test_default_thresholds(self):
        """Test default safety threshold values."""
        thresholds = SafetyThresholds()
        
        assert thresholds.warn_file_count == 100
        assert thresholds.critical_file_count == 1000
        assert thresholds.warn_total_size == 50 * 1024 * 1024  # 50MB
        assert thresholds.critical_total_size == 500 * 1024 * 1024  # 500MB
        assert thresholds.warn_large_file == 5 * 1024 * 1024  # 5MB
        assert thresholds.critical_large_file == 50 * 1024 * 1024  # 50MB
    
    def test_custom_thresholds(self):
        """Test custom safety threshold configuration."""
        thresholds = SafetyThresholds(
            warn_file_count=50,
            critical_file_count=500,
            warn_total_size=10 * 1024 * 1024,
            critical_total_size=100 * 1024 * 1024
        )
        
        assert thresholds.warn_file_count == 50
        assert thresholds.critical_file_count == 500
        assert thresholds.warn_total_size == 10 * 1024 * 1024
        assert thresholds.critical_total_size == 100 * 1024 * 1024


class TestSafetyReport:
    """Test safety report functionality."""
    
    def test_safety_report_creation(self):
        """Test safety report creation with basic data."""
        files = [Path("test1.js"), Path("test2.js")]
        
        report = SafetyReport(
            operation="minify",
            total_files=2,
            total_size=1024 * 1024,  # 1MB
            large_files=[],
            is_safe=True,
            risk_level="low",
            warnings=[],
            recommendations=[]
        )
        
        assert report.operation == "minify"
        assert report.total_files == 2
        assert report.total_size_mb == 1.0
        assert report.requires_confirmation == False  # low risk
    
    def test_safety_report_high_risk(self):
        """Test safety report for high risk operations."""
        large_files = [(Path("large.js"), 10 * 1024 * 1024)]
        
        report = SafetyReport(
            operation="format",
            total_files=150,
            total_size=60 * 1024 * 1024,  # 60MB
            large_files=large_files,
            is_safe=False,
            risk_level="high",
            warnings=["🔶 Large operation: 150 files", "🔶 Large total size: 60.0MB"],
            recommendations=["Review file list with --dry-run first"]
        )
        
        assert report.risk_level == "high"
        assert report.requires_confirmation == True  # high risk
        assert len(report.warnings) == 2
        assert len(report.recommendations) == 1
        assert report.total_size_mb == 60.0


class TestSafetyChecker:
    """Test safety checker functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.safety_checker = SafetyChecker()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Cleanup test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, name: str, size: int) -> Path:
        """Create a test file with specified size."""
        file_path = self.temp_dir / name
        file_path.write_bytes(b'x' * size)
        return file_path
    
    def test_low_risk_operation(self):
        """Test analysis of low risk operation (few small files)."""
        files = [
            self.create_test_file("small1.js", 1024),  # 1KB
            self.create_test_file("small2.js", 2048),  # 2KB
        ]
        
        report = self.safety_checker.analyze_operation(files, "minify")
        
        assert report.total_files == 2
        assert report.risk_level == "low"
        assert report.is_safe == True
        assert len(report.warnings) == 0
        assert not report.requires_confirmation
    
    def test_high_risk_file_count(self):
        """Test analysis with high file count (>100 files)."""
        files = []
        for i in range(150):
            files.append(self.create_test_file(f"file_{i}.js", 1024))
        
        report = self.safety_checker.analyze_operation(files, "minify")
        
        assert report.total_files == 150
        assert report.risk_level == "high"
        assert any("Large operation: 150 files" in warning for warning in report.warnings)
        assert any("Double-check that all files should be processed" in rec for rec in report.recommendations)
        assert report.requires_confirmation
    
    def test_critical_risk_file_count(self):
        """Test analysis with critical file count (>1000 files)."""
        # Mock file creation for performance
        files = []
        for i in range(1500):
            file_path = self.temp_dir / f"file_{i}.js"
            files.append(file_path)
            
        # Mock file.stat() to avoid actually creating 1500 files
        with patch('pathlib.Path.stat') as mock_stat:
            mock_stat.return_value.st_size = 1024  # 1KB each file
            
            report = self.safety_checker.analyze_operation(files, "format")
            
            assert report.total_files == 1500
            assert report.risk_level == "critical"
            assert report.is_safe == False
            assert any("Very large operation: 1,500 files" in warning for warning in report.warnings)
            assert any("Consider processing in smaller batches" in rec for rec in report.recommendations)
    
    def test_large_file_detection(self):
        """Test detection of large individual files."""
        files = [
            self.create_test_file("normal.js", 1024 * 1024),     # 1MB - normal
            self.create_test_file("large.js", 10 * 1024 * 1024), # 10MB - large
            self.create_test_file("huge.js", 60 * 1024 * 1024),  # 60MB - critical
        ]
        
        report = self.safety_checker.analyze_operation(files, "minify")
        
        assert report.risk_level == "critical"
        assert len(report.large_files) == 2  # large.js and huge.js
        assert any("very large files (>50MB)" in warning for warning in report.warnings)
        
        # Check specific large files
        large_file_sizes = [size for _, size in report.large_files]
        assert 10 * 1024 * 1024 in large_file_sizes  # 10MB file
        assert 60 * 1024 * 1024 in large_file_sizes  # 60MB file
    
    def test_total_size_warnings(self):
        """Test warnings based on total size."""
        # Create files totaling ~60MB (above 50MB threshold)
        files = []
        for i in range(12):
            files.append(self.create_test_file(f"medium_{i}.js", 5 * 1024 * 1024))  # 5MB each
        
        report = self.safety_checker.analyze_operation(files, "format")
        
        assert report.total_size > 50 * 1024 * 1024  # Above warning threshold
        assert report.risk_level == "high"
        assert any("Large total size" in warning for warning in report.warnings)
    
    def test_git_repository_detection(self):
        """Test git repository detection."""
        # Create a mock .git directory
        git_dir = self.temp_dir / '.git'
        git_dir.mkdir()
        
        is_git_repo, warning = self.safety_checker.should_warn_about_git_repo(self.temp_dir)
        
        assert is_git_repo == True
        assert "Processing entire git repository" in warning
    
    def test_operation_summary(self):
        """Test comprehensive operation summary generation."""
        files = [
            self.create_test_file("test1.js", 2 * 1024 * 1024),  # 2MB
            self.create_test_file("test2.js", 3 * 1024 * 1024),  # 3MB
        ]
        
        summary = self.safety_checker.get_operation_summary(files, "minify", dry_run=False)
        
        assert 'safety_report' in summary
        assert 'is_git_repo' in summary
        assert 'git_warning' in summary
        assert 'dry_run' in summary
        assert 'summary' in summary
        
        # Check summary format
        summary_text = summary['summary']
        assert "Files: 2" in summary_text
        assert "Total size:" in summary_text
        assert "Risk level:" in summary_text
    
    def test_format_safety_summary(self):
        """Test safety summary formatting."""
        files = [self.create_test_file("test.js", 1024 * 1024)]  # 1MB
        report = self.safety_checker.analyze_operation(files, "minify")
        
        summary = self.safety_checker.format_safety_summary(report)
        
        assert "Files: 1" in summary
        assert "Total size: 1.0MB" in summary
        assert "Risk level: LOW" in summary


class TestUserConfirmation:
    """Test user confirmation functionality."""
    
    def test_low_risk_no_confirmation(self):
        """Test that low risk operations don't require confirmation."""
        summary = {
            'safety_report': SafetyReport(
                operation="minify",
                total_files=5,
                total_size=1024 * 1024,
                large_files=[],
                is_safe=True,
                risk_level="low",
                warnings=[],
                recommendations=[]
            ),
            'is_git_repo': False,
            'git_warning': "",
            'dry_run': False,
            'summary': "Files: 5 | Total size: 1.0MB | Risk level: LOW"
        }
        
        # Low risk should return True without prompting
        result = get_user_confirmation("minify", summary)
        assert result == True
    
    @patch('builtins.input', return_value='y')
    def test_high_risk_user_accepts(self, mock_input):
        """Test high risk operation with user accepting."""
        summary = {
            'safety_report': SafetyReport(
                operation="format",
                total_files=150,
                total_size=60 * 1024 * 1024,
                large_files=[],
                is_safe=False,
                risk_level="high",
                warnings=["🔶 Large operation: 150 files"],
                recommendations=["Review file list with --dry-run first"]
            ),
            'is_git_repo': False,
            'git_warning': "",
            'dry_run': False,
            'summary': "Files: 150 | Total size: 60.0MB | Risk level: HIGH"
        }
        
        result = get_user_confirmation("format", summary)
        assert result == True
    
    @patch('builtins.input', return_value='n')
    def test_high_risk_user_declines(self, mock_input):
        """Test high risk operation with user declining."""
        summary = {
            'safety_report': SafetyReport(
                operation="minify",
                total_files=1200,
                total_size=600 * 1024 * 1024,
                large_files=[],
                is_safe=False,
                risk_level="critical",
                warnings=["⚠️  Very large operation: 1,200 files"],
                recommendations=["Consider processing in smaller batches"]
            ),
            'is_git_repo': True,
            'git_warning': "⚠️  Processing entire git repository: /path/to/repo",
            'dry_run': False,
            'summary': "Files: 1,200 | Total size: 600.0MB | Risk level: CRITICAL"
        }
        
        result = get_user_confirmation("minify", summary)
        assert result == False
    
    @patch('builtins.input', side_effect=KeyboardInterrupt())
    def test_user_interrupts_confirmation(self, mock_input):
        """Test user interrupting confirmation with Ctrl+C."""
        summary = {
            'safety_report': SafetyReport(
                operation="format",
                total_files=200,
                total_size=100 * 1024 * 1024,
                large_files=[],
                is_safe=False,
                risk_level="high",
                warnings=["🔶 Large operation: 200 files"],
                recommendations=["Review file list with --dry-run first"]
            ),
            'is_git_repo': False,
            'git_warning': "",
            'dry_run': False,
            'summary': "Files: 200 | Total size: 100.0MB | Risk level: HIGH"
        }
        
        result = get_user_confirmation("format", summary)
        assert result == False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__])