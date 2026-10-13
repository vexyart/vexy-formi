# Python API

The package `vexy_formi` exposes the same machinery `vfor` uses. The calls on this page do not ask for confirmation, whatever the number of files; use `dry_run=True` while you try them out.

## Quick calls

```python
import vexy_formi

result = vexy_formi.format("src/", dry_run=True)
print(result)
```

```text
{'success': True, 'total_files': 7, 'successful': 7, 'failed': 0, 'total_time': 0.068…, 'errors': []}
```

`vexy_formi.format(path, **kwargs)` and `vexy_formi.minify(path, **kwargs)` are thin wrappers around `format_files()` and `minify_files()`. `path` is a string, a `Path` or a list of either.

Keyword arguments are passed to `FileProcessor.format_files()` or `FileProcessor.minify_files()`:

| Keyword | Default | Meaning |
| --- | --- | --- |
| `recursive` | `True` | Descend into subdirectories |
| `exclude_patterns` | `None` | Extra gitignore-style patterns |
| `max_workers` | `4` | Parallel workers |
| `create_backup` | `True` | Accepted, but no backup is written; see [Safety and backups](safety.md) |
| `dry_run` | `False` | Pick tools but run none |
| `progress_callback` | `None` | Called after each file; see below |

!!! note
    The keyword is `exclude_patterns`, not `exclude`. `vexy_formi.format("src/", exclude=[...])` raises `TypeError: FileProcessor.format_files() got an unexpected keyword argument 'exclude'`.

The return value is a dictionary:

| Key | Meaning |
| --- | --- |
| `success` | `True` if at least one file succeeded |
| `total_files` | Files found |
| `successful`, `failed` | Counts |
| `total_time` | Seconds |
| `errors` | Error messages of the failed files |
| `size_reduction_bytes`, `size_reduction_percent` | Only from `minify` |

## FileProcessor

For full results, use the class directly.

```python
from pathlib import Path

from vexy_formi import FileProcessor

processor = FileProcessor()
result = processor.format_files(Path("src"), exclude_patterns=["*.py"], dry_run=True)
print(result.total_files, result.successful, result.success_rate)

for r in result.results:
    print(r.path.name, r.success, r.tool_used, r.error_message)
```

`FileProcessor(config=None)` loads the [configuration](configuration.md) when `config` is `None`.

| Method | Returns |
| --- | --- |
| `format_files(paths, recursive=True, exclude_patterns=None, max_workers=4, create_backup=True, dry_run=False, progress_callback=None)` | `BatchResult` |
| `minify_files(...)` | `BatchResult`, same arguments |
| `format_file(file_path, create_backup=True, dry_run=False)` | `ProcessResult` |
| `minify_file(file_path, create_backup=True, dry_run=False)` | `ProcessResult` |

`BatchResult` fields: `total_files`, `successful`, `failed`, `total_time`, `total_size_before`, `total_size_after`, `results` (a list of `ProcessResult`). Properties: `success_rate`, `total_size_reduction`, `total_size_reduction_percent`.

`ProcessResult` fields: `path`, `success`, `original_size`, `final_size`, `tool_used`, `processing_time`, `error_message`. Properties: `size_reduction_percent`, `size_change`. In a dry run, `tool_used` ends in ` (dry-run)`.

### Progress callback

The callback is called from the main thread after each file finishes:

```python
def on_progress(result, completed, total):
    print(f"{completed}/{total} {result.path.name}: {'ok' if result.success else result.error_message}")

processor.minify_files(Path("site"), progress_callback=on_progress, dry_run=True)
```

## Helpers

```python
from pathlib import Path

from vexy_formi import detect_file_type, find_files, get_available_tools, validate_file

detect_file_type(Path("a.py"))          # 'python'
detect_file_type(Path("a.xyz"))         # None
validate_file(Path("src/app.py"))       # (True, None) or (False, "reason")
find_files(Path("src"), {".py", ".js"}) # list of Path, after exclusions and ignore files
get_available_tools()                   # names of tools found so far, e.g. ['ruff', 'biome', 'black']
```

- `detect_file_type()` and `validate_file()` take a `Path`, not a string.
- `find_files(directory, extensions, exclude_patterns=None, recursive=True, respect_gitignore=True)` applies the same exclusions and ignore files as `vfor`.
- `get_available_tools()` lists only tools that have been checked so far. Tools are checked lazily (see [Tools and file types](tools.md#the-tool-cache)), so the list can be shorter than what `vfor tools` shows.

## ToolManager

`ToolManager(config=None)` holds the tool lists and runs the tools.

```python
from pathlib import Path

from vexy_formi import ToolManager

tm = ToolManager()
tm.is_available("ruff")                       # True or False
tm.get_format_command(Path("a.py"))           # ('ruff', ['ruff', 'format', '{input}'])
tm.get_minify_command_with_fallback(Path("a.js"))  # all installed minifiers for .js, in order
tm.supports_minify(Path("a.py"))              # False
```

`tm.minify_commands` and `tm.format_commands` are the dictionaries described in [Tools and file types](tools.md).
