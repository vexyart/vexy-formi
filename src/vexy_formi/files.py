#!/usr/bin/env python3
# this_file: src/vexy_formi/files.py
"""
Simple file operations for vexy-formi.

Simplified version focusing on essential file operations: basic validation,
atomic writes, and file discovery. Removes complex enterprise validation
while preserving safety.
"""

import os
import shutil
import tempfile
import chardet
import stat
from pathlib import Path
from typing import List, Optional, Tuple, Set, Iterator
import pathspec

class FileHandler:
    """Simple file handler with basic validation and atomic operations."""
    
    def __init__(self, max_file_size: int = 100 * 1024 * 1024):
        """
        Initialize file handler.
        
        Args:
            max_file_size: Maximum file size to process (default 100MB)
        """
        self.max_file_size = max_file_size
        
        # Default exclusion patterns
        self.default_exclusions = [
            '.git/**',
            'node_modules/**',
            '.venv/**',
            'venv/**',
            '__pycache__/**',
            'target/**',  # Rust
            'dist/**',
            'build/**',
            '.next/**',
            '.nuxt/**',
            'coverage/**',
            '*.min.js',
            '*.min.css',
            '*.min.html',
            '.DS_Store',
            'Thumbs.db',
            '*.backup',
            '*.bak',
            '*~',
        ]
    
    def validate_file(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Simple file validation.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check if file exists
            if not file_path.exists():
                return False, f"File does not exist: {file_path}"
            
            # Check if it's actually a file
            if not file_path.is_file():
                return False, f"Path is not a file: {file_path}"
            
            # Check file size
            try:
                file_size = file_path.stat().st_size
                if file_size > self.max_file_size:
                    return False, f"File too large ({file_size} bytes): {file_path}"
                if file_size == 0:
                    return False, f"Empty file: {file_path}"
            except OSError as e:
                return False, f"Cannot check file size: {e}"
            
            # Check if readable
            if not os.access(file_path, os.R_OK):
                detailed_error = self.diagnose_permission_error(file_path, "read")
                return False, detailed_error
            
            # Check if writable
            if not os.access(file_path, os.W_OK):
                detailed_error = self.diagnose_permission_error(file_path, "write")
                return False, detailed_error
            
            # Basic binary file check (simple heuristic)
            if self._is_likely_binary(file_path):
                return False, f"Binary file detected: {file_path}"
            
            # Check for file corruption and integrity
            corruption_check = self._check_file_integrity(file_path)
            if not corruption_check[0]:
                return False, corruption_check[1]
            
            # Check if file is locked or in use
            lock_check = self._check_file_lock_status(file_path)
            if not lock_check[0]:
                return False, lock_check[1]
            
            # Check for encoding and special character issues
            encoding_check = self._check_file_encoding(file_path)
            if not encoding_check[0]:
                return False, encoding_check[1]
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def _is_likely_binary(self, file_path: Path) -> bool:
        """Improved binary file detection using multiple heuristics."""
        try:
            # Check file extension first (fastest)
            binary_extensions = {
                '.exe', '.dll', '.so', '.dylib', '.bin', '.app',
                '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp', '.ico', '.svg',
                '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac', '.ogg',
                '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
                '.zip', '.tar', '.gz', '.bz2', '.7z', '.rar',
                '.ttf', '.otf', '.woff', '.woff2',
                '.class', '.jar', '.war', '.ear',
                '.pyc', '.pyo', '.pyd',
                '.o', '.obj', '.lib', '.a',
            }
            
            ext = file_path.suffix.lower()
            if ext in binary_extensions:
                return True
            
            # Known text extensions (bypass deeper checks)
            text_extensions = {
                '.txt', '.md', '.rst', '.log', '.ini', '.cfg', '.conf',
                '.json', '.xml', '.yaml', '.yml', '.toml', '.csv',
                '.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs',
                '.py', '.pyw', '.pyi', '.rb', '.php', '.pl', '.sh', '.bat',
                '.css', '.scss', '.sass', '.less', '.html', '.htm', '.xhtml',
                '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp', '.hxx',
                '.java', '.kt', '.scala', '.go', '.rs', '.swift',
                '.sql', '.graphql', '.proto', '.dockerfile',
            }
            
            if ext in text_extensions:
                return False
            
            # Read sample for content analysis
            sample_size = min(8192, file_path.stat().st_size)  # Up to 8KB sample
            with open(file_path, 'rb') as f:
                chunk = f.read(sample_size)
            
            if not chunk:  # Empty file
                return False
            
            # Check for null bytes (strong indicator of binary)
            null_count = chunk.count(b'\x00')
            if null_count > 0:
                # Allow a few null bytes in text files (some encodings)
                null_ratio = null_count / len(chunk)
                if null_ratio > 0.05:  # More than 5% null bytes  
                    return True
                # If there are null bytes but not many, continue with other checks
            
            # Check for non-printable ASCII characters (excluding null bytes already counted)
            non_printable_count = 0
            for byte in chunk:
                # Count bytes that are not printable ASCII or common whitespace
                # Exclude null bytes since we handle them separately above
                if byte < 32 and byte not in (0, 9, 10, 13):  # not null, tab, LF, CR
                    non_printable_count += 1
                elif byte > 126:  # Extended ASCII
                    # Allow some extended ASCII for UTF-8 text
                    pass
            
            non_printable_ratio = non_printable_count / len(chunk)
            if non_printable_ratio > 0.05:  # More than 5% non-printable
                return True
            
            # Try charset detection
            try:
                result = chardet.detect(chunk)
                if result:
                    confidence = result.get('confidence', 0)
                    encoding = result.get('encoding', '').lower()
                    
                    # If confidence is very low, likely binary
                    if confidence < 0.3:
                        return True
                    
                    # Some encodings are more reliable indicators
                    if encoding in ('utf-8', 'ascii', 'utf-16', 'utf-32'):
                        return False
                        
                    # If we can decode successfully, probably text
                    try:
                        chunk.decode(result['encoding'])
                        return False
                    except (UnicodeDecodeError, LookupError):
                        return True
                
            except Exception:
                pass  # Chardet failed, continue with other checks
            
            # Try UTF-8 decode as last resort
            try:
                chunk.decode('utf-8')
                return False
            except UnicodeDecodeError:
                try:
                    chunk.decode('latin-1')  # Can decode anything, but check quality
                    # If we got here, it might be text in latin-1
                    # Do a final check for text-like patterns
                    text = chunk.decode('latin-1')
                    # Look for common text patterns
                    if any(pattern in text.lower() for pattern in [
                        'function', 'class', 'import', 'const', 'let', 'var',
                        '<html', '<?xml', 'def ', 'if ', 'for ', 'while ',
                        '#!/', '/*', '//', '#', '{', '}', '[', ']'
                    ]):
                        return False
                    
                    # If no text patterns found, probably binary
                    return True
                    
                except UnicodeDecodeError:
                    return True
            
        except Exception:
            return True  # Assume binary if we can't analyze it properly
    
    def _check_file_integrity(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Simple file integrity check.
        
        Args:
            file_path: Path to check
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Basic check: try to open and read a small portion
            with open(file_path, 'rb') as f:
                # Read up to 4KB to check for basic readability
                f.read(4096)
            return True, None
        except OSError as e:
            return False, f"File integrity issue: {e}"
        except Exception as e:
            return False, f"Unexpected error reading file: {e}"
    
    def _check_file_lock_status(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Check if file is locked or in use.
        
        Args:
            file_path: Path to check
            
        Returns:
            Tuple of (is_available, error_message)
        """
        try:
            # Simple check: try to open in append mode (least intrusive)
            with open(file_path, 'a'):
                pass
            return True, None
        except PermissionError:
            return False, f"File is locked or permission denied: {file_path}"
        except OSError as e:
            return False, f"File access error: {e}"
        except Exception as e:
            return False, f"Unexpected error checking file lock: {e}"
    
    def _check_file_encoding(self, file_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Check file encoding and readability.
        
        Args:
            file_path: Path to check
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Read a sample to check encoding
            with open(file_path, 'rb') as f:
                sample = f.read(8192)  # 8KB sample
            
            if not sample:
                return True, None  # Empty files are valid
            
            # Try to detect encoding
            try:
                result = chardet.detect(sample)
                if result and result.get('confidence', 0) > 0.5:
                    encoding = result['encoding']
                    try:
                        sample.decode(encoding)
                        return True, None
                    except (UnicodeDecodeError, LookupError):
                        pass
            except Exception:
                pass
            
            # Fallback: try common encodings
            for encoding in ['utf-8', 'utf-16', 'latin-1']:
                try:
                    sample.decode(encoding)
                    return True, None
                except UnicodeDecodeError:
                    continue
            
            return False, f"Cannot determine valid encoding for file: {file_path}"
            
        except Exception as e:
            return False, f"Error checking file encoding: {e}"
    
    def find_files(self, 
                  directory: Path, 
                  extensions: Set[str], 
                  exclude_patterns: Optional[List[str]] = None,
                  recursive: bool = True,
                  lazy_validation: bool = False,
                  respect_gitignore: bool = True) -> List[Path]:
        """
        Optimized file finding for large directory trees with .gitignore support.
        
        Args:
            directory: Directory to search
            extensions: Set of file extensions to include (e.g., {'.js', '.py'})
            exclude_patterns: Additional exclusion patterns (gitignore-style)
            recursive: Whether to search recursively
            lazy_validation: Skip file validation for better performance
            respect_gitignore: Automatically load and respect .gitignore/.vforignore files
            
        Returns:
            List of found file paths
            
        Note:
            Supports gitignore-style patterns:
            - `*.log` - ignore all .log files
            - `node_modules/` - ignore node_modules directory
            - `build/**` - ignore everything in build directory
            - `!important.txt` - negate pattern (don't ignore this file)
            - `temp/` - ignore directory
            - `*.min.*` - ignore minified files
        """
        if not directory.exists() or not directory.is_dir():
            return []
        
        # Combine default, gitignore, and custom exclusions
        all_patterns = self.default_exclusions.copy()
        
        # Load gitignore-style files if requested
        if respect_gitignore:
            gitignore_patterns = self._load_gitignore_patterns(directory)
            all_patterns.extend(gitignore_patterns)
        
        # Add custom patterns
        if exclude_patterns:
            all_patterns.extend(exclude_patterns)
        spec = pathspec.PathSpec.from_lines('gitwildmatch', all_patterns)
        
        # Separate directory and file exclusion patterns for better performance
        dir_patterns = []
        file_patterns = []
        for pattern in all_patterns:
            if '**' in pattern or pattern.endswith('/'):
                dir_patterns.append(pattern)
            else:
                file_patterns.append(pattern)
        
        dir_spec = pathspec.PathSpec.from_lines('gitwildmatch', dir_patterns) if dir_patterns else None
        file_spec = pathspec.PathSpec.from_lines('gitwildmatch', file_patterns) if file_patterns else None
        
        return list(self._optimized_file_iterator(
            directory, extensions, dir_spec, file_spec, recursive, lazy_validation
        ))
    
    def _optimized_file_iterator(self, 
                               directory: Path,
                               extensions: Set[str],
                               dir_spec: Optional,
                               file_spec: Optional, 
                               recursive: bool,
                               lazy_validation: bool):
        """
        Optimized iterator for file discovery with early filtering.
        """
        try:
            # Use os.walk for better control over directory traversal
            if recursive:
                for root, dirs, files in os.walk(directory):
                    root_path = Path(root)
                    
                    # Early directory filtering - skip entire directories
                    if dir_spec:
                        try:
                            relative_root = root_path.relative_to(directory)
                            if dir_spec.match_file(str(relative_root)):
                                dirs.clear()  # Skip this directory tree
                                continue
                        except ValueError:
                            continue
                    
                    # Filter directories in-place to avoid traversing excluded ones
                    if dir_spec:
                        dirs[:] = [d for d in dirs 
                                 if not dir_spec.match_file(str(Path(root) / d))]
                    
                    # Process files with early extension filtering
                    for filename in files:
                        file_path = root_path / filename
                        
                        # Early extension check - most efficient filter
                        if file_path.suffix.lower() not in extensions:
                            continue
                        
                        # File-level exclusion check
                        if file_spec:
                            try:
                                relative_path = file_path.relative_to(directory)
                                if file_spec.match_file(str(relative_path)):
                                    continue
                            except ValueError:
                                continue
                        
                        # Skip validation for performance if requested
                        if lazy_validation:
                            yield file_path
                        else:
                            # Only validate files that passed all other filters
                            is_valid, _ = self.validate_file(file_path)
                            if is_valid:
                                yield file_path
            else:
                # Non-recursive: only check immediate directory
                try:
                    for item in directory.iterdir():
                        if not item.is_file():
                            continue
                        
                        # Early extension check
                        if item.suffix.lower() not in extensions:
                            continue
                        
                        # File exclusion check
                        if file_spec and file_spec.match_file(item.name):
                            continue
                        
                        # Validation
                        if lazy_validation:
                            yield item
                        else:
                            is_valid, _ = self.validate_file(item)
                            if is_valid:
                                yield item
                except PermissionError:
                    # Provide detailed error diagnosis but continue processing
                    should_continue, error_msg = self.handle_permission_error(directory, "read", continue_on_error=True)
                    # Note: In a real implementation, you might want to log this error
                    # For now, we continue silently but could add logging here
                    pass
        except Exception:
            # Gracefully handle any traversal errors
            pass
    
    def _load_gitignore_patterns(self, directory: Path) -> List[str]:
        """
        Load gitignore-style patterns from .gitignore and .vforignore files.
        
        Args:
            directory: Directory to search for ignore files
            
        Returns:
            List of patterns from gitignore files
        """
        patterns = []
        
        # Files to check (in order of precedence - later files override earlier ones)
        ignore_files = [
            directory / '.gitignore',
            directory / '.vforignore',  # VFor-specific ignore file
            directory.parent / '.gitignore',  # Parent directory gitignore
            Path.home() / '.vforignore_global',  # Global VFor ignore file
        ]
        
        for ignore_file in ignore_files:
            if ignore_file.exists() and ignore_file.is_file():
                try:
                    with open(ignore_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            # Skip empty lines and comments
                            if line and not line.startswith('#'):
                                patterns.append(line)
                except Exception:
                    # If we can't read the file, continue without it
                    continue
        
        return patterns
    
    def create_vforignore_file(self, directory: Path, patterns: Optional[List[str]] = None) -> bool:
        """
        Create a .vforignore file with common exclusion patterns.
        
        Args:
            directory: Directory to create the file in
            patterns: Custom patterns to include, or None for defaults
            
        Returns:
            True if file was created successfully
        """
        if patterns is None:
            patterns = [
                "# VFor ignore file - gitignore-style patterns for code formatting",
                "# See: https://git-scm.com/docs/gitignore for syntax",
                "",
                "# Dependencies",
                "node_modules/",
                ".venv/", 
                "venv/",
                "vendor/",
                "",
                "# Build outputs",
                "dist/",
                "build/",
                "*.min.js",
                "*.min.css", 
                "*.min.html",
                "",
                "# Temporary files",
                "*.tmp",
                "*.temp",
                "*.log",
                ".DS_Store",
                "Thumbs.db",
                "",
                "# VFor backup files (already excluded by default)",
                "*.vfor_backup",
                "*.vfor_temp",
                "",
                "# IDE and editor files",
                ".vscode/",
                ".idea/",
                "*.swp",
                "*~",
                "",
                "# Examples of advanced patterns:",
                "# !important.txt     # Negate: don't ignore this file",
                "# temp/**           # Ignore everything in temp directory", 
                "# *.test.*          # Ignore test files",
                "# src/**/generated/ # Ignore generated directories",
            ]
        
        vforignore_path = directory / '.vforignore'
        
        try:
            with open(vforignore_path, 'w', encoding='utf-8') as f:
                for pattern in patterns:
                    f.write(pattern + '\n')
            return True
        except Exception:
            return False
    
    def atomic_write(self, file_path: Path, content: bytes, create_backup: bool = True) -> bool:
        """
        Atomic file write with optional backup.
        
        Args:
            file_path: Target file path
            content: Content to write
            create_backup: Whether to create a backup
            
        Returns:
            True if successful, False otherwise
        """
        backup_path = None
        
        try:
            # Create backup if requested and file exists
            if create_backup and file_path.exists():
                backup_path = file_path.with_suffix(file_path.suffix + '.vfor_backup')
                shutil.copy2(file_path, backup_path)
            
            # Write to temporary file first
            temp_path = file_path.with_suffix(file_path.suffix + '.vfor_temp')
            
            with open(temp_path, 'wb') as f:
                f.write(content)
            
            # Atomic move (replace original)
            if os.name == 'nt':  # Windows
                if file_path.exists():
                    file_path.unlink()
                temp_path.rename(file_path)
            else:  # Unix-like
                temp_path.rename(file_path)
            
            # Clean up backup on success (optional)
            if backup_path and backup_path.exists():
                # Keep backup for safety, user can clean up manually
                pass
            
            return True
            
        except Exception as e:
            # Clean up temp file
            temp_path = file_path.with_suffix(file_path.suffix + '.vfor_temp')
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except:
                    pass
            
            # Restore from backup if write failed
            if backup_path and backup_path.exists() and not file_path.exists():
                try:
                    shutil.copy2(backup_path, file_path)
                except:
                    pass
            
            return False
    
    def atomic_write_text(self, file_path: Path, content: str, encoding: str = 'utf-8', create_backup: bool = True) -> bool:
        """
        Atomic text file write.
        
        Args:
            file_path: Target file path
            content: Text content to write
            encoding: Text encoding
            create_backup: Whether to create a backup
            
        Returns:
            True if successful, False otherwise
        """
        try:
            content_bytes = content.encode(encoding)
            return self.atomic_write(file_path, content_bytes, create_backup)
        except UnicodeEncodeError:
            return False
    
    def read_text_file(self, file_path: Path) -> Optional[Tuple[str, str]]:
        """
        Read text file with encoding detection.
        
        Args:
            file_path: File to read
            
        Returns:
            Tuple of (content, encoding) or None if failed
        """
        try:
            # Try UTF-8 first (most common)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return content, 'utf-8'
            except UnicodeDecodeError:
                pass
            
            # Detect encoding
            with open(file_path, 'rb') as f:
                raw_content = f.read()
            
            result = chardet.detect(raw_content)
            if result and result.get('confidence', 0) > 0.5:
                encoding = result['encoding']
                try:
                    content = raw_content.decode(encoding)
                    return content, encoding
                except (UnicodeDecodeError, LookupError):
                    pass
            
            # Fallback to latin-1 (can decode anything)
            content = raw_content.decode('latin-1')
            return content, 'latin-1'
            
        except Exception:
            return None
    
    def get_file_info(self, file_path: Path) -> Optional[dict]:
        """
        Get basic file information.
        
        Args:
            file_path: File to analyze
            
        Returns:
            Dictionary with file info or None if failed
        """
        try:
            stat_result = file_path.stat()
            
            return {
                'path': str(file_path),
                'size': stat_result.st_size,
                'modified': stat_result.st_mtime,
                'readable': os.access(file_path, os.R_OK),
                'writable': os.access(file_path, os.W_OK),
                'extension': file_path.suffix.lower(),
                'name': file_path.name,
            }
        except Exception:
            return None
    
    def cleanup_backups(self, directory: Path) -> int:
        """
        Clean up backup files in directory.
        
        Args:
            directory: Directory to clean
            
        Returns:
            Number of backup files removed
        """
        count = 0
        for pattern in ['*.vfor_backup', '*.vfor_temp']:
            for backup_file in directory.glob(pattern):
                try:
                    backup_file.unlink()
                    count += 1
                except:
                    pass
        
        return count

    def diagnose_permission_error(self, path: Path, operation: str = "access") -> str:
        """
        Analyze permission errors and provide actionable suggestions.
        
        Args:
            path: Path that caused the permission error
            operation: Type of operation that failed (access, read, write)
            
        Returns:
            Detailed error message with actionable suggestions
        """
        try:
            # Get current user info
            current_uid = os.getuid() if hasattr(os, 'getuid') else None
            current_gid = os.getgid() if hasattr(os, 'getgid') else None
            
            # Get file/directory info
            is_dir = path.is_dir()
            file_type = "directory" if is_dir else "file"
            
            # Get permission info if possible
            try:
                path_stat = path.stat()
                file_mode = stat.filemode(path_stat.st_mode)
                file_uid = path_stat.st_uid
                file_gid = path_stat.st_gid
                
                # Check ownership
                is_owner = current_uid == file_uid if current_uid is not None else False
                is_group_member = current_gid == file_gid if current_gid is not None else False
                
                suggestions = []
                
                # Ownership-based suggestions
                if not is_owner and current_uid is not None:
                    if current_uid == 0:  # Running as root
                        suggestions.append("You're running as root - consider changing ownership or using a regular user")
                    else:
                        suggestions.append(f"Change ownership: sudo chown $USER {path}")
                        suggestions.append(f"Or change permissions: sudo chmod u+rw {path}")
                
                # Permission-based suggestions  
                if operation == "read":
                    suggestions.append(f"Make readable: chmod +r {path}")
                elif operation == "write":
                    suggestions.append(f"Make writable: chmod +w {path}")
                    if is_dir:
                        suggestions.append(f"Allow directory access: chmod +x {path}")
                elif operation == "access":
                    if is_dir:
                        suggestions.append(f"Allow directory access: chmod +x {path}")
                    else:
                        suggestions.append(f"Make accessible: chmod +r {path}")
                
                # Directory-specific advice
                if is_dir and operation == "write":
                    suggestions.append("Ensure you have write permission to create/modify files in this directory")
                
                error_msg = f"Permission denied for {file_type}: {path}\\n"
                error_msg += f"Current permissions: {file_mode}\\n"
                error_msg += "Suggestions:\\n"
                for i, suggestion in enumerate(suggestions[:3], 1):  # Limit to top 3 suggestions
                    error_msg += f"  {i}. {suggestion}\\n"
                
                return error_msg.strip()
                
            except OSError:
                # Can't get detailed info
                return f"Permission denied accessing {file_type}: {path}\\nTry: sudo chmod +rw {path}"
                
        except Exception:
            # Fallback for any error in diagnosis
            return f"Permission error with {path}. Try running with elevated privileges or check file permissions."

    def handle_permission_error(self, path: Path, operation: str, continue_on_error: bool = True) -> Tuple[bool, str]:
        """
        Handle permission errors with detailed diagnosis and optional continuation.
        
        Args:
            path: Path that caused the error
            operation: Operation that failed
            continue_on_error: Whether to continue processing other files
            
        Returns:
            Tuple of (should_continue, error_message)
        """
        detailed_error = self.diagnose_permission_error(path, operation)
        
        if continue_on_error:
            return True, detailed_error
        else:
            return False, detailed_error

def find_files(directory: Path, 
               extensions: Set[str], 
               exclude_patterns: Optional[List[str]] = None,
               recursive: bool = True,
               respect_gitignore: bool = True) -> List[Path]:
    """Convenience function for finding files with gitignore support."""
    handler = FileHandler()
    return handler.find_files(directory, extensions, exclude_patterns, recursive, respect_gitignore=respect_gitignore)

def validate_file(file_path: Path) -> Tuple[bool, Optional[str]]:
    """Convenience function for validating a file."""
    handler = FileHandler()
    return handler.validate_file(file_path)