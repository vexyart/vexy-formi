# CLI reference

`vfor` is built with [Python Fire](https://github.com/google/python-fire) from the `VFor` class in `src/vexy_formi/cli.py`. Run `vfor` with no command to list the commands.

## How arguments work

- A positional argument can also be given by name: `vfor fmt src/` and `vfor fmt --path=src/` are the same.
- Boolean flags switch on by name (`--verbose`) and off with a `no` prefix (`--nobackup`, `--norecursive`).
- Flag names use underscores: `--dry_run`, `--create_baseline`.
- Most flags also have a one-letter form, shown below.
- List values are written as Python-style lists: `--exclude='["*.min.js", "vendor/**"]'`.
- To see a command's flags without running it, put `--` before `--help`:

    ```bash
    vfor mini -- --help
    ```

## fmt

Format files in place.

```bash
vfor fmt                    # current directory, recursively
vfor fmt src/
vfor fmt app.py
vfor fmt src/ --norecursive # top level of src/ only
vfor fmt src/ --dry_run --verbose
```

| Flag | Short | Default | Meaning |
| --- | --- | --- | --- |
| `--path` | `-p` | `.` | File or directory to process |
| `--recursive` | `-r` | on | Descend into subdirectories |
| `--exclude` | `-e` | none | Extra exclusion patterns, as a list |
| `--verbose` | `-v` | off | Print each file and a per-file result list |
| `--backup` | `-b` | on | Intended to keep a backup of each file; see the note below |
| `--dry_run` | `-d` | off | Find files and pick tools, but run nothing |
| `--force` | `-f` | off | Skip the confirmation for large runs |

!!! note "`--backup` has no effect in this version"
    The flag is passed along, but the code path that runs the tools does not write backup files. See [Safety and backups](safety.md).

The extensions `fmt` handles are listed in [Tools and file types](tools.md#format).

## mini

Minify files in place. Same flags as `fmt`.

```bash
vfor mini dist-src/
vfor mini site/ --exclude='["*.min.*"]' --verbose
```

The extensions `mini` handles are listed in [Tools and file types](tools.md#minify). Files whose type has no minifier, such as `.py`, are not picked up when you give a directory; a single file of such a type fails with `No minification tool available for .py`.

## Output of `fmt` and `mini`

While running, a progress bar shows the counts of successful and failed files, the size saved and the rate in files per second. At the end:

- `Failed: <n> files`, if any failed.
- `Processed <n> files`, followed for `mini` by the total size change, for example `+6.0% size`. With `--verbose` the elapsed time follows; with `--dry_run`, `(preview)`.
- With `--verbose`, a `Failed files:` list with each error, and a `Successful files:` list. For `mini` each line shows `original → final bytes, ±percent`; for `fmt` it shows the time taken.

A positive percentage means the file got smaller.

## tools

```bash
vfor tools
```

Show the 13 tools `vfor` knows about, whether each is installed, its type (minifier, formatter or processor), its implementation language and the formats it covers. Installed tools come first, then tools written in Rust or Go. The last lines count the available tools.

## install

```bash
vfor install
vfor install --verbose
```

Install Homebrew, Node.js and a fixed set of tools, then write `dprint.json`, `biome.json`, `ruff.toml` and `.vfor.json` into the current directory if they are missing. The full list of actions is in [Installation](installation.md#option-2-vfor-install).

## update

```bash
vfor update
vfor update --verbose
```

Update Homebrew, npm and Rust, update the installed tools, clean the package manager caches, check each tool and refresh the plugin list in `./dprint.json`. See [Installation](installation.md#updating-the-tools).

## configure

```bash
vfor configure init    # write an example .vfor.json in the current directory
vfor configure show    # print the effective settings and which config files exist
vfor configure         # print usage (action defaults to help)
```

`init` refuses to overwrite an existing `.vfor.json`. `show` lists `max_workers`, `preferred_js_tool`, `preferred_css_tool`, `preferred_python_tool` and `create_backup`, each with a source of `default`, `environment` or `config file`. The source column is a simple guess: it says `config file` whenever `./.vfor.json` exists, even if that file does not set the value. See [Configuration](configuration.md).

## ignore

```bash
vfor ignore init [path]   # write .vforignore with common patterns into path
vfor ignore show [path]   # list the patterns that apply in path
vfor ignore help          # print usage and pattern examples
```

`action` defaults to `init` and `path` to the current directory. `init` overwrites an existing `.vforignore`. `show` lists the first 20 patterns read from the ignore files described in [Configuration](configuration.md#ignore-files).

## cleanup

```bash
vfor cleanup
vfor cleanup src/ --norecursive
```

Delete files ending in `.vfor_backup` or `.vfor_temp` below the path. Prints how many were removed, or `No backup files found`.

## benchmark

```bash
vfor benchmark src/
vfor benchmark src/ --operation=format --verbose
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `path` | `.` | Directory or file |
| `operation` | `both` | `minify`, `format` or `both` |
| `verbose` | off | Show more detail |

The benchmark runs the operation in dry-run mode, so no file is changed and no tool is executed. It measures file discovery, validation and tool selection, and reports counts and timings per extension.

## perf_check

```bash
vfor perf_check src/ --create_baseline   # record a baseline
vfor perf_check src/                     # compare against it
```

| Argument | Default | Meaning |
| --- | --- | --- |
| `path` | `.` | Directory to measure |
| `operation` | `both` | `minify`, `format` or `both` |
| `create_baseline` | off | Save a new baseline instead of comparing |

Baselines are stored in `~/.cache/vfor/performance_baselines.json`. A slow-down of more than 15 % against the baseline counts as a regression.

## Exit status

`vfor` exits with `1` when it is interrupted with <kbd>Ctrl</kbd>+<kbd>C</kbd> and when an uncaught `FileNotFoundError`, `PermissionError` or other exception reaches the top level. An unknown command or bad argument makes Fire exit with `2`.

Files that fail to process do not change the exit status, and neither does a path that does not exist: `vfor fmt nonexistent --force` prints nothing and exits with `0`. Check the `Failed:` and `Processed` lines when you script around `vfor`.
