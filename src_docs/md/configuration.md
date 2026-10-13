# Configuration

`vfor` reads settings from three places, in this order. A later source overrides an earlier one.

1. Built-in defaults.
2. JSON config files.
3. Environment variables.

Flags on the command line apply to one run only.

## Settings

| Key | Default | Used for |
| --- | --- | --- |
| `max_workers` | `4` | Number of files processed in parallel by `fmt`, `mini`, `benchmark` |
| `exclude_patterns` | see below | Patterns added to every run's exclusions |
| `preferred_js_tool` | `esbuild` | Shown by `vfor configure show`; does not change tool choice in this version |
| `preferred_css_tool` | `biome` | As above |
| `preferred_python_tool` | `ruff` | As above |
| `preferred_html_tool` | `html-minifier-terser` | Not shown, not used |
| `create_backup` | `true` | Shown by `vfor configure show`; not used. The `--backup` flag decides, and it has no effect either; see [Safety and backups](safety.md) |

Default `exclude_patterns`:

```json
[".git/**", "node_modules/**", ".venv/**", "venv/**", "__pycache__/**", "target/**",
 "dist/**", "build/**", "*.min.js", "*.min.css", "*.min.html", ".DS_Store", "Thumbs.db"]
```

## Config files

`vfor` looks for these files. When more than one exists, values from the higher one in this list win:

| File | Scope |
| --- | --- |
| `./.vfor.json` | The directory you run `vfor` from |
| `~/.vfor/config.json` | Your user account |
| `/etc/vfor/config.json` | The whole machine |

A file must contain one JSON object. A file that is not valid JSON, or holds something other than an object, is ignored without a message.

`exclude_patterns` in a file replaces the default list rather than adding to it. Repeat the defaults you want to keep.

Create a starting point with:

```bash
vfor configure init
```

This writes `./.vfor.json`:

```json
{
    "preferred_js_tool": "esbuild",
    "preferred_css_tool": "biome",
    "preferred_python_tool": "ruff",
    "preferred_html_tool": "html-minifier-terser",
    "max_workers": 4,
    "create_backup": true,
    "exclude_patterns": [
        "*.min.*",
        "node_modules/**",
        "dist/**",
        "build/**",
        ".git/**"
    ]
}
```

Check what `vfor` sees with:

```bash
vfor configure show
```

## Environment variables

| Variable | Setting | Accepted values |
| --- | --- | --- |
| `VFOR_MAX_WORKERS` | `max_workers` | An integer |
| `VFOR_PREFERRED_JS_TOOL` | `preferred_js_tool` | Any string |
| `VFOR_PREFERRED_CSS_TOOL` | `preferred_css_tool` | Any string |
| `VFOR_PREFERRED_PYTHON_TOOL` | `preferred_python_tool` | Any string |
| `VFOR_PREFERRED_HTML_TOOL` | `preferred_html_tool` | Any string |
| `VFOR_CREATE_BACKUP` | `create_backup` | `true`, `1`, `yes` (anything else is false) |
| `VFOR_VERBOSE` | `verbose` | Read into the settings but not used by any command |

An invalid value, such as `VFOR_MAX_WORKERS=many`, is ignored.

```bash
VFOR_MAX_WORKERS=8 vfor fmt src/
```

## Exclusion patterns

For each run, the exclusion list is built from four parts:

1. A fixed list in the file handler: the defaults above plus `.next/**`, `.nuxt/**`, `coverage/**`, `*.backup`, `*.bak` and `*~`.
2. Patterns from the ignore files described below.
3. `exclude_patterns` from the settings.
4. The `--exclude` list from the command line.

Patterns use `.gitignore` syntax: `*.log` matches a file name anywhere, `build/` or `build/**` a directory, and `!keep.txt` re-includes a file.

## Ignore files

`vfor` reads gitignore-style patterns from these files, relative to the directory being processed:

1. `<dir>/.gitignore`
2. `<dir>/.vforignore`
3. `<dir>/../.gitignore` (the parent directory)
4. `~/.vforignore_global`

Blank lines and lines starting with `#` are skipped. All patterns from all four files are combined.

`vfor ignore init <dir>` writes a `.vforignore` with patterns for dependencies (`node_modules/`, `.venv/`, `venv/`, `vendor/`), build output (`dist/`, `build/`, `*.min.js`, `*.min.css`, `*.min.html`), temporary files (`*.tmp`, `*.temp`, `*.log`, `.DS_Store`, `Thumbs.db`), backup files (`*.vfor_backup`, `*.vfor_temp`) and editor files (`.vscode/`, `.idea/`, `*.swp`, `*~`). `vfor ignore show <dir>` prints the first 20 patterns found.

## Files `vfor` writes outside your project

| Path | Written by | Content |
| --- | --- | --- |
| `~/.cache/vfor/tool_cache.json` | every command | Which tools are installed, valid for one hour |
| `~/.cache/vfor/performance_baselines.json` | `perf_check` | Performance baselines |
