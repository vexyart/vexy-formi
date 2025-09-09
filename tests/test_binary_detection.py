#!/usr/bin/env python3
# this_file: tests/test_binary_detection.py
"""
Test binary file detection accuracy.

Tests the improved binary file detection logic with various file types.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add src to path for testing
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from vexy_formi.files import FileHandler


class TestBinaryDetection:
    """Test binary file detection."""
    
    def setup_method(self):
        """Setup test environment."""
        self.file_handler = FileHandler()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def create_test_file(self, filename: str, content: bytes) -> Path:
        """Create a test file with given content."""
        file_path = self.temp_dir / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        return file_path
    
    def test_text_file_extensions(self):
        """Test that known text files are detected as text."""
        text_files = [
            ("test.js", b'function test() { console.log("hello"); }'),
            ("test.py", b'def hello():\n    print("world")'),
            ("test.css", b'.test { color: red; }'),
            ("test.html", b'<html><body>Hello</body></html>'),
            ("test.json", b'{"name": "test", "value": 123}'),
            ("test.md", b'# Test Markdown\n\nHello world'),
            ("test.txt", b'This is plain text'),
            ("test.yaml", b'name: test\nvalue: 123'),
            ("test.toml", b'[section]\nname = "test"'),
        ]
        
        for filename, content in text_files:
            file_path = self.create_test_file(filename, content)
            is_binary = self.file_handler._is_likely_binary(file_path)
            assert not is_binary, f"{filename} should be detected as text, not binary"
            print(f"✓ {filename} correctly detected as text")
    
    def test_binary_file_extensions(self):
        """Test that known binary files are detected as binary."""
        # Create fake binary files with binary-like content
        binary_files = [
            ("test.jpg", b'\xff\xd8\xff\xe0\x00\x10JFIF'),  # JPEG header
            ("test.png", b'\x89PNG\r\n\x1a\n'),  # PNG header
            ("test.pdf", b'%PDF-1.4'),  # PDF header
            ("test.exe", b'MZ\x90\x00'),  # EXE header
            ("test.zip", b'PK\x03\x04'),  # ZIP header
            ("test.pyc", b'\x03\xf3\r\n\x00\x00\x00\x00'),  # Python bytecode
        ]
        
        for filename, content in binary_files:
            file_path = self.create_test_file(filename, content)
            is_binary = self.file_handler._is_likely_binary(file_path)
            assert is_binary, f"{filename} should be detected as binary"
            print(f"✓ {filename} correctly detected as binary")
    
    def test_content_based_detection(self):
        """Test content-based binary detection."""
        # Text file with no extension but text content
        text_no_ext = self.create_test_file(
            "textfile",
            b'#!/bin/bash\necho "Hello World"\n# This is a comment\n'
        )
        is_binary = self.file_handler._is_likely_binary(text_no_ext)
        assert not is_binary, "Text content should be detected as text even without extension"
        print("✓ Text content without extension correctly detected as text")
        
        # Binary content with many null bytes
        binary_content = self.create_test_file(
            "binaryfile",
            b'\x00\x01\x02\x03\x00\x00\x00\xff' * 100
        )
        is_binary = self.file_handler._is_likely_binary(binary_content)
        assert is_binary, "Content with many null bytes should be detected as binary"
        print("✓ Binary content correctly detected as binary")
        
        # Mixed content (mostly text with some binary)
        mixed_content = self.create_test_file(
            "mixedfile",
            b'function test() {\n    console.log("hello");\n}\x00\x01\x02'
        )
        is_binary = self.file_handler._is_likely_binary(mixed_content)
        # This should be detected as text since it's mostly text content
        assert not is_binary, "Mostly text content should be detected as text"
        print("✓ Mixed content with mostly text correctly detected as text")
    
    def test_utf8_files(self):
        """Test UTF-8 encoded files."""
        utf8_content = self.create_test_file(
            "utf8.txt",
            "Hello 世界! 🌍 Здравствуй мир!".encode('utf-8')
        )
        is_binary = self.file_handler._is_likely_binary(utf8_content)
        assert not is_binary, "UTF-8 encoded text should be detected as text"
        print("✓ UTF-8 content correctly detected as text")
    
    def test_empty_files(self):
        """Test empty files."""
        empty_file = self.create_test_file("empty.txt", b'')
        is_binary = self.file_handler._is_likely_binary(empty_file)
        assert not is_binary, "Empty file should be detected as text"
        print("✓ Empty file correctly detected as text")
    
    def test_large_text_file(self):
        """Test large text files."""
        # Create a large text file
        large_content = b'// This is a JavaScript file\n' * 1000
        large_file = self.create_test_file("large.js", large_content)
        is_binary = self.file_handler._is_likely_binary(large_file)
        assert not is_binary, "Large text file should be detected as text"
        print("✓ Large text file correctly detected as text")


def run_binary_detection_tests():
    """Run all binary detection tests."""
    print("🔍 Running Binary Detection Tests")
    print("=" * 50)
    
    tester = TestBinaryDetection()
    
    try:
        tester.setup_method()
        
        print("\n📝 Text File Extension Tests")
        tester.test_text_file_extensions()
        
        print("\n🔢 Binary File Extension Tests")  
        tester.test_binary_file_extensions()
        
        print("\n🔍 Content-Based Detection Tests")
        tester.test_content_based_detection()
        
        print("\n🌍 UTF-8 File Tests")
        tester.test_utf8_files()
        
        print("\n📄 Empty File Tests")
        tester.test_empty_files()
        
        print("\n📚 Large File Tests")
        tester.test_large_text_file()
        
        print("\n✅ Binary detection tests completed!")
        
    except Exception as e:
        print(f"\n❌ Binary detection test failed: {e}")
        raise
        
    finally:
        tester.teardown_method()


if __name__ == "__main__":
    run_binary_detection_tests()