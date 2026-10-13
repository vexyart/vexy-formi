# Safety and backups

`vfor fmt` and `vfor mini` rewrite your files in place. This page describes what `vfor` checks before it touches a file, when it asks for confirmation, and what it does not do.

## Use version control

The most reliable undo is `git`. Commit or stash before a run, then review the result:

```bash
git stash            # or: git commit -am "before vfor"
vfor fmt src/
git diff --stat
```

If you do not like the result, `git checkout -- src/` restores the files.

## Backups are not written in this version

The README, the `--backup` flag (on by default) and the `create_backup` setting all describe backup files. In version 1.0.x, none are written:

- `fmt` and `mini` hand each file to the external tool, which writes its output straight over the original. That code path receives the backup setting but does not use it.
- A test run of `vfor mini` and `vfor fmt` on the sample files left no `*.vfor_backup` file behind, and `vfor cleanup` reported `No backup files found`.

The library does contain an atomic-write helper (`FileHandler.atomic_write`) that copies the original to `<name>.vfor_backup`, writes to a temporary file and renames it, but `fmt` and `mini` do not call it. `vfor cleanup` exists to remove `.vfor_backup` and `.vfor_temp` files left by such writes.

## What is skipped

Before a file is processed it must pass these checks. A file that fails one is reported as failed, with the reason, and left unchanged.

| Check | Failure message starts with |
| --- | --- |
| The path exists and is a regular file | `File does not exist` / `Path is not a file` |
| Size is not zero and not over 100 MB | `Empty file` / `File too large` |
| Readable and writable by you | a permission diagnosis |
| Not binary: no known binary extension (`.png`, `.pdf`, `.zip`, `.svg`, `.exe`, …) and content that looks like text | `Binary file detected` |
| Can be opened for appending, so it is not locked | `File is locked or permission denied` |
| Its encoding can be detected and decoded | an encoding message |
| A tool exists for its extension | `No minification tool available for .<ext>` / `No formatting tool available for .<ext>` |

When you give a directory, files are also filtered by extension and by the exclusion patterns described in [Configuration](configuration.md#exclusion-patterns), before any of these checks.

## When `vfor` asks for confirmation

Before a real run (not `--dry_run`), unless you pass `--force`, `vfor` collects the list of files and rates the run:

| Condition | Risk |
| --- | --- |
| 1000 files or more | critical |
| 500 MB or more in total | critical |
| Any single file of 50 MB or more | critical |
| 100 files or more | high |
| 50 MB or more in total | high |
| Anything else | low |

For a high or critical run, `vfor` prints the summary, any warnings (for example that the path is inside a git repository), recommendations and the risk level, then asks:

```text
Do you want to continue? [y/N]:
```

Anything other than `y` or `yes` cancels the run with `Operation cancelled`. <kbd>Ctrl</kbd>+<kbd>C</kbd> also cancels it.

In scripts, use `--force` to skip the question, or `--dry_run` to check first.

## Dry runs

`--dry_run` goes through file discovery, validation and tool selection, then stops. It does not start any tool. The sizes it reports are estimates from fixed ratios, for example 65 % of the original for `.js` when minifying and 110 % for `.json` when formatting. Use it to see which files would be touched and which tool each would get, not to predict the result.

## Parallel processing

Files are processed by a pool of `max_workers` threads (four by default). Each file is handled by one tool at a time, so a file is never written by two tools at once. The order in which files finish, and in which `--verbose` lists them, is not fixed.
