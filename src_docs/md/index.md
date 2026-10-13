# vexy-formi

`vexy-formi` formats and minifies source files by handing each file to an external tool that is already installed on your machine: `ruff` or `black` for Python, `biome`, `prettier` or `dprint` for JavaScript and CSS, `esbuild` or `swc` to minify JavaScript, and so on. It finds the files, picks a tool per file type, runs the tools in parallel and reports what happened.

The package installs one command, `vfor`, and a Python package, `vexy_formi`.

## What goes in, what comes out

You give `vfor` a directory or a file and an operation:

- `vfor fmt <path>` formats every supported file in place.
- `vfor mini <path>` minifies every supported file in place.

For each file the tool:

1. Skips it if it matches an exclusion pattern, is empty, larger than 100 MB, binary, unreadable or not writable.
2. Looks up the file's extension in a fixed list of tools for that operation, for example `.py` → `ruff`, then `black`.
3. Runs the first tool that is installed. If that tool fails, it tries the next one.
4. Records the size before and after.

At the end it prints a summary such as `Processed 4 files`. With `--verbose` it lists each file.

```bash
vfor fmt src/ --verbose
```

```text
Successful files:
  test.json (0.116s)
  test.js (0.122s)
  test.css (0.024s)
  test.py (0.149s)
```

## What it is not

- It is not a formatter itself. Without the external tools it does nothing. `vfor tools` shows which are installed; `vfor install` tries to install them.
- It does not read each tool's settings for you. A tool such as `dprint` still needs its own `dprint.json`.
- It is not reversible. The files are rewritten in place; see [Safety and backups](safety.md) before you run it on work you have not committed.

## Where to go next

| If you want to… | Read |
| --- | --- |
| Install `vfor` and the tools it calls | [Installation](installation.md) |
| Format a project for the first time | [Quick start](quickstart.md) |
| Look up a command or flag | [CLI reference](cli.md) |
| See which tool handles which file type | [Tools and file types](tools.md) |
| Change worker count or exclusion patterns | [Configuration](configuration.md) |
| Understand what is skipped, what is asked, what is backed up | [Safety and backups](safety.md) |
| Call it from Python | [Python API](python-api.md) |
| Fix a problem | [Troubleshooting](troubleshooting.md) |
| Work on the code | [Development](development.md) |
