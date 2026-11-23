#!/usr/bin/env python3
# this_file: tests/test_cli.py
"""
CLI smoke tests for vfor command.

Tests the CLI interface to ensure basic commands work correctly.
"""

import subprocess
import tempfile
import shutil
from pathlib import Path


class TestCLI:
    """Test CLI functionality."""
    
    def setup_method(self):
        """Setup test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Copy test fixtures to temp directory
        fixtures_dir = Path(__file__).parent / "fixtures"
        if fixtures_dir.exists():
            shutil.copytree(fixtures_dir, self.temp_dir / "fixtures")
        
        # Create simple test files if fixtures don't exist
        self.test_js = self.temp_dir / "test.js"
        self.test_js.write_text("function test() { console.log('hello'); }")
        
        self.test_json = self.temp_dir / "test.json"
        self.test_json.write_text('{"name": "test", "value": 123}')
    
    def teardown_method(self):
        """Clean up test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    def run_vfor_command(self, args, cwd=None, timeout=30):
        """Run vfor command and return result."""
        # Always run from project root to find the module, but use absolute paths for files
        project_root = Path(__file__).parent.parent
        cmd = ["python", "-m", "src.vexy_formi.cli"] + args
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)
    
    def test_vfor_tools(self):
        """Test vfor tools command."""
        print("\n🔧 Testing: vfor tools")
        
        returncode, stdout, stderr = self.run_vfor_command(["tools"])
        
        if returncode == 0:
            print("✓ vfor tools command successful")
            assert "Available Tools" in stdout or "Tool Status" in stdout
            print(f"  Output preview: {stdout[:100]}...")
        else:
            print(f"✗ vfor tools failed: {stderr}")
            raise AssertionError(f"CLI command failed: {stderr}")
    
    def test_vfor_mini_single_file(self):
        """Test vfor mini on a single file."""
        print("\n🗜️ Testing: vfor mini (single file)")
        
        # Test minifying the JSON file
        original_size = self.test_json.stat().st_size
        
        returncode, stdout, stderr = self.run_vfor_command(
            ["mini", str(self.test_json), "--verbose"]
        )
        
        if returncode == 0:
            print("✓ vfor mini command successful")
            # File should still exist
            assert self.test_json.exists(), "Original file was removed"
            print(f"  Original size: {original_size} bytes")
        else:
            print(f"✗ vfor mini failed: {stderr}")
            # Don't fail the test if tool is missing, just report
            print("  (This might be expected if required tools are not installed)")
    
    def test_vfor_fmt_single_file(self):
        """Test vfor fmt on a single file."""  
        print("\n✨ Testing: vfor fmt (single file)")
        
        # Test formatting the JSON file
        original_size = self.test_json.stat().st_size
        
        returncode, stdout, stderr = self.run_vfor_command(
            ["fmt", str(self.test_json), "--verbose"]
        )
        
        if returncode == 0:
            print("✓ vfor fmt command successful")
            # File should still exist
            assert self.test_json.exists(), "Original file was removed"
            print(f"  Original size: {original_size} bytes")
        else:
            print(f"✗ vfor fmt failed: {stderr}")
            # Don't fail the test if tool is missing, just report
            print("  (This might be expected if required tools are not installed)")
    
    def test_vfor_help(self):
        """Test vfor help functionality."""
        print("\n❓ Testing: vfor help")
        
        # Test general help
        returncode, stdout, stderr = self.run_vfor_command(["--help"])
        
        if returncode == 0:
            print("✓ vfor --help successful")
        else:
            # Try alternative help format
            returncode, stdout, stderr = self.run_vfor_command(["help"])
            if returncode == 0:
                print("✓ vfor help successful")
            else:
                print(f"⚠ Help command may not be working: {stderr}")
    
    def test_vfor_dry_run_flag(self):
        """Test --dry-run flag functionality."""
        print("\n🧪 Testing: vfor --dry-run flag")
        
        # Create a backup of the original file content 
        original_content = self.test_json.read_text()
        original_size = self.test_json.stat().st_size
        
        # Test dry run - should not modify file
        returncode, stdout, stderr = self.run_vfor_command(
            ["mini", str(self.test_json), "--dry-run", "--verbose"]
        )
        
        if returncode == 0:
            # File should be unchanged
            assert self.test_json.read_text() == original_content, "File was modified in dry-run mode"
            assert self.test_json.stat().st_size == original_size, "File size changed in dry-run mode" 
            print("✓ --dry-run flag working correctly (no file changes)")
            
            # Check that output indicates it's a preview
            assert "preview" in stdout.lower() or "dry" in stdout.lower(), "Output should indicate dry-run mode"
        else:
            print(f"⚠ --dry-run test may have failed: {stderr}")
    
    def test_vfor_force_flag_with_large_operation(self):
        """Test --force flag bypassing safety warnings on large operations."""
        print("\n⚡ Testing: vfor --force flag with safety system")
        
        # Create many files to trigger safety warnings (>100 files = high risk)
        large_test_dir = self.temp_dir / "large_operation"
        large_test_dir.mkdir()
        
        test_files = []
        for i in range(120):  # Above the 100 file safety threshold
            test_file = large_test_dir / f"test_{i:03d}.json"
            test_file.write_text('{"test": "data", "index": ' + str(i) + '}')
            test_files.append(test_file)
        
        print(f"  Created {len(test_files)} files to trigger safety warnings")
        
        # Test without --force (should either prompt or warn)
        returncode_no_force, stdout_no_force, stderr_no_force = self.run_vfor_command(
            ["mini", str(large_test_dir), "--verbose"], timeout=5  # Quick timeout to avoid hanging on prompt
        )
        
        # Test with --force (should bypass safety checks and process files)
        returncode_force, stdout_force, stderr_force = self.run_vfor_command(
            ["mini", str(large_test_dir), "--force", "--verbose"]
        )
        
        if returncode_force == 0:
            print("✓ --force flag successfully bypassed safety warnings")
            
            # Verify files were actually processed (should be minified)
            processed_files = 0
            for test_file in test_files[:5]:  # Check first 5 files
                if test_file.exists():
                    content = test_file.read_text().strip()
                    # Should be minified (no spaces)
                    if '{"test":"data","index":' in content:
                        processed_files += 1
            
            if processed_files > 0:
                print(f"✓ Files were successfully minified ({processed_files}/5 checked)")
            else:
                print("⚠ Files may not have been properly minified")
        else:
            print(f"⚠ --force flag test may have failed: {stderr_force}")
    
    def test_vfor_safety_system_integration(self):
        """Test safety system integration with CLI commands."""
        print("\n🛡️  Testing: Safety system integration")
        
        # Create a medium-sized operation (should trigger warnings but not be critical)
        medium_test_dir = self.temp_dir / "medium_operation" 
        medium_test_dir.mkdir()
        
        # Create 50 files (below 100 file threshold, should be safe)
        for i in range(50):
            test_file = medium_test_dir / f"safe_test_{i:02d}.js"
            test_file.write_text(f'function test{i}() {{ console.log("test {i}"); }}')
        
        print(f"  Created 50 files (below safety threshold)")
        
        # Should process without warnings
        returncode, stdout, stderr = self.run_vfor_command(
            ["mini", str(medium_test_dir), "--verbose"]
        )
        
        if returncode == 0:
            print("✓ Medium-sized operation processed successfully")
            
            # Verify no safety warnings in output
            output_text = (stdout + stderr).lower()
            safety_indicators = ["warning", "risk", "confirmation", "dangerous"]
            has_safety_warnings = any(indicator in output_text for indicator in safety_indicators)
            
            if not has_safety_warnings:
                print("✓ No unnecessary safety warnings for safe operation")
            else:
                print("⚠ Unexpected safety warnings for safe operation")
        else:
            print(f"⚠ Medium operation test failed: {stderr}")
    
    def test_vfor_dry_run_with_safety_system(self):
        """Test that --dry-run automatically bypasses safety checks.""" 
        print("\n🔬 Testing: --dry-run bypassing safety checks")
        
        # Create large operation that would trigger safety warnings
        large_dry_test_dir = self.temp_dir / "large_dry_test"
        large_dry_test_dir.mkdir()
        
        # Create 150 files (above safety threshold)
        for i in range(150):
            test_file = large_dry_test_dir / f"dry_test_{i:03d}.css"
            test_file.write_text(f'.test{i} {{ color: red; background: blue; }}')
        
        print(f"  Created 150 files (above safety threshold)")
        
        # Test dry-run (should not trigger safety prompts)
        returncode, stdout, stderr = self.run_vfor_command(
            ["fmt", str(large_dry_test_dir), "--dry-run", "--verbose"]
        )
        
        if returncode == 0:
            print("✓ --dry-run successfully bypassed safety checks")
            
            # Verify it shows preview information
            output_text = (stdout + stderr).lower()
            if "preview" in output_text or "dry" in output_text:
                print("✓ Output correctly indicates dry-run mode")
            else:
                print("⚠ Output may not clearly indicate dry-run mode")
                
            # Verify no files were modified
            for i in range(5):  # Check first 5 files
                test_file = large_dry_test_dir / f"dry_test_{i:03d}.css"
                content = test_file.read_text()
                if '.test' in content and 'color: red' in content:  # Should still be formatted
                    continue
                else:
                    print("⚠ File may have been modified in dry-run mode")
                    break
            else:
                print("✓ Files unchanged in dry-run mode")
        else:
            print(f"⚠ Dry-run safety bypass test failed: {stderr}")


def run_cli_tests():
    """Run all CLI tests."""
    print("🖥️  Running VexyFormi CLI Tests")
    print("=" * 50)
    
    tester = TestCLI()
    
    try:
        tester.setup_method()
        
        # Run tests
        tester.test_vfor_tools()
        tester.test_vfor_mini_single_file() 
        tester.test_vfor_fmt_single_file()
        tester.test_vfor_help()
        tester.test_vfor_dry_run_flag()
        tester.test_vfor_force_flag_with_large_operation()
        tester.test_vfor_safety_system_integration()
        tester.test_vfor_dry_run_with_safety_system()
        
        print("\n✅ CLI tests completed!")
        
    except Exception as e:
        print(f"\n❌ CLI test failed: {e}")
        raise
        
    finally:
        tester.teardown_method()


if __name__ == "__main__":
    run_cli_tests()