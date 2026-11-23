#!/usr/bin/env python3
# this_file: tests/test_basic.py
"""
Basic smoke tests for vexy-formi functionality.

Tests core functionality with various file formats and verifies
that the tool can handle different scenarios gracefully.
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path for testing
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from vexy_formi import FileProcessor, ToolManager
from vexy_formi.files import FileHandler


class TestBasicFunctionality:
    """Test basic vexy-formi functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.processor = FileProcessor()
        self.tool_manager = ToolManager()
        self.file_handler = FileHandler()
        self.fixtures_dir = Path(__file__).parent / "fixtures"
        
        # Create temporary directory for tests
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Copy test fixtures to temp directory
        if self.fixtures_dir.exists():
            shutil.copytree(self.fixtures_dir, self.temp_dir / "fixtures")
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def test_tool_detection(self):
        """Test that tool manager can detect available tools."""
        available_tools = self.tool_manager.get_available_tools()
        
        # Should find at least some tools (even built-in ones)
        assert len(available_tools) > 0, "No tools detected"
        
        # Test tool info
        tool_info = self.tool_manager.get_tool_info()
        assert len(tool_info) > 0, "No tool info available"
        
        print(f"✓ Detected {len(available_tools)} tools: {', '.join(available_tools)}")
    
    def test_file_validation(self):
        """Test file validation works correctly."""
        fixtures = self.temp_dir / "fixtures"
        
        if not fixtures.exists():
            print("⚠ No test fixtures available, skipping file validation test")
            return
        
        test_files = list(fixtures.glob("test.*"))
        assert len(test_files) > 0, "No test files found"
        
        for test_file in test_files:
            is_valid, error_msg = self.file_handler.validate_file(test_file)
            if is_valid:
                print(f"✓ {test_file.name} passed validation")
            else:
                print(f"✗ {test_file.name} failed validation: {error_msg}")
    
    def test_format_support(self):
        """Check format support for a known set of installed tools."""
        from unittest.mock import patch

        installed = {"esbuild", "biome", "ruff", "jq", "html-minifier-terser"}
        test_cases = [
            ("test.js", True, True),    # Should support both minify and format
            ("test.css", True, True),   # Should support both
            ("test.py", False, True),   # Should support format only  
            ("test.json", True, True),  # Should support both
            ("test.html", True, True),  # Should support both
            ("test.unknown", False, False),  # Should support neither
        ]
        
        with patch.object(self.tool_manager, "is_available", side_effect=installed.__contains__):
            for filename, should_minify, should_format in test_cases:
                test_path = Path(filename)
                assert self.tool_manager.supports_minify(test_path) == should_minify, filename
                assert self.tool_manager.supports_format(test_path) == should_format, filename

            installed.remove("esbuild")
            assert not self.tool_manager.supports_minify(Path("test.js"))
    
    def test_tool_fallback(self):
        """Test tool fallback logic when preferred tools are missing."""
        # Test with a file that has multiple tool options
        js_file = Path("test.js") 
        
        minify_command = self.tool_manager.get_minify_command(js_file)
        format_command = self.tool_manager.get_format_command(js_file)
        
        if minify_command:
            tool_name, command = minify_command
            print(f"✓ JS minify fallback: {tool_name}")
        else:
            print("⚠ No JS minify tools available")
        
        if format_command:
            tool_name, command = format_command  
            print(f"✓ JS format fallback: {tool_name}")
        else:
            print("⚠ No JS format tools available")
    
    def test_file_processing(self):
        """Test actual file processing with available tools."""
        fixtures = self.temp_dir / "fixtures"
        
        if not fixtures.exists():
            print("⚠ No test fixtures available, skipping processing test")
            return
        
        # Try to process a simple file
        test_files = [
            (fixtures / "test.py", "format"),
            (fixtures / "test.json", "format"),
        ]
        
        for test_file, operation in test_files:
            if not test_file.exists():
                continue
                
            original_size = test_file.stat().st_size
            
            try:
                if operation == "minify":
                    result = self.processor.minify_file(test_file, create_backup=True)
                else:
                    result = self.processor.format_file(test_file, create_backup=True)
                
                if result.success:
                    print(f"✓ {test_file.name} {operation} successful with {result.tool_used}")
                    print(f"  Size: {result.original_size} → {result.final_size} bytes")
                else:
                    print(f"✗ {test_file.name} {operation} failed: {result.error_message}")
                    
            except Exception as e:
                print(f"✗ {test_file.name} {operation} error: {e}")


def run_basic_tests():
    """Run all basic tests."""
    print("🧪 Running VexyFormi Basic Tests")
    print("=" * 50)
    
    tester = TestBasicFunctionality()
    
    try:
        tester.setup_method()
        
        print("\n📋 Tool Detection Test")
        tester.test_tool_detection()
        
        print("\n🔍 File Validation Test") 
        tester.test_file_validation()
        
        print("\n📄 Format Support Test")
        tester.test_format_support()
        
        print("\n🔄 Tool Fallback Test")
        tester.test_tool_fallback()
        
        print("\n⚡ File Processing Test")
        tester.test_file_processing()
        
        print("\n✅ Basic tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        raise
        
    finally:
        tester.teardown_method()


if __name__ == "__main__":
    run_basic_tests()