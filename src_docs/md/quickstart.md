# Quick start

This page formats a small project, previews a minification, and then minifies. It follows the seven sample files that ship in the repository under `tests/fixtures/`: `test.css`, `test.html`, `test.js`, `test.json`, `test.md`, `test.py` and `test.toml`.

## Prerequisites

- `vfor` is installed. See [Installation](installation.md).
- The project is under version control and committed, or you work on a copy. `vfor` rewrites files in place and, in this version, does not keep backups; see [Safety and backups](safety.md).

## 1. Make a test project

Copy the sample files into a scratch directory called `proj`:

```bash
git clone https://github.com/vexyart/vexy-formi.git
mkdir proj
cp vexy-formi/tests/fixtures/* proj/
```

## 2. See which tools you have

```bash
vfor tools
```

On the machine used for this page, six of the 13 tools were available:

```text
│ biome   │ ✓ Available │ Formatter │ Rust   │ JS, TS, JSON, CSS │
│ dprint  │ ✓ Available │ Formatter │ Rust   │ Multiple          │
│ ruff    │ ✓ Available │ Formatter │ Rust   │ Python            │
│ yq      │ ✓ Available │ Processor │ Go     │ YAML              │
│ black   │ ✓ Available │ Formatter │ Python │ Python            │
│ jq      │ ✓ Available │ Processor │ C      │ JSON              │
│ esbuild │ ✗ Missing   │ Minifier  │ Go     │ JS, TS            │
...
6/13 tools available
4 fast tools (Rust/Go) available
```

Which files `vfor` can process depends on this list. [Tools and file types](tools.md) shows which tool handles which extension.

## 3. Preview the formatting

`--dry_run` finds the files and picks a tool for each, but runs nothing and changes nothing.

```bash
vfor fmt proj --dry_run --verbose
```

```text
Processed 7 files  (preview)
```

In a dry run, the sizes shown are estimates from fixed ratios, not real results.

## 4. Format

```bash
vfor fmt proj --verbose
```

`vfor` runs the tools in parallel, four files at a time by default. In this run four files succeeded and three failed. The TOML file, for example, failed because `taplo` was missing and `dprint` found no `dprint.json`:

```text
  test.toml: All format tools failed - dprint: dprint: No config file found at …/dprint.json. …

Successful files:
  test.json (0.116s)
  test.js (0.122s)
  test.css (0.024s)
  test.py (0.149s)
```

The number after each file is how long its tool took.

## 5. Preview a minification

```bash
vfor mini proj --dry_run --verbose
```

```text
Failed files:
  test.html: No minification tool available for .html
  test.js: No minification tool available for .js

Successful files:
  test.json (617 → 493 bytes, +20.1%)
  test.css (608 → 425 bytes, +30.1%)
```

Without `esbuild`, `swc` or `terser`, JavaScript cannot be minified; without `html-minifier-terser`, HTML cannot either. Python, Markdown and TOML are never minified.

A positive percentage is a size reduction.

## 6. Minify

```bash
vfor mini proj --verbose
```

```text
  ✓ test.json (+20.6%)
  ✓ test.css (+9.2%)

Failed: 2 files
Processed 2 files, +6.0% size (0.12s)
```

`test.json` is now on one line, compacted by `jq -c`. `test.css` was rewritten by `biome format --write`, the fallback when `lightningcss` is missing; that is formatting, not true minification, which is why it shrank by only 9.2%.

## 7. Exclude files

Pass extra exclusion patterns to `--exclude` as a list:

```bash
vfor fmt proj --exclude='["*.py", "legacy/**"]'
```

!!! warning
    Give `--exclude` a list in square brackets. A bare string such as `--exclude "*.py"` is split into single characters, one of which is `*`, and every file is excluded.

For patterns you use every time, create a `.vforignore` file:

```bash
vfor ignore init proj
```

## 8. Large runs

When a run touches 100 files or more, 50 MB or more in total, or a single file of 50 MB or more, `vfor` prints a summary and asks `Do you want to continue? [y/N]`. Answer `y` to go on. Add `--force` to skip the question, for example in scripts.

```bash
vfor fmt src/ --force
```
