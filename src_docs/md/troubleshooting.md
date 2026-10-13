# Troubleshooting

Start with:

```bash
vfor tools              # which tools are installed?
vfor configure show     # which settings are in effect?
vfor fmt src/ --dry_run --verbose   # which files would be touched, with which tool?
```

## Nothing happens

### `vfor fmt` prints nothing at all

No files were found. Check:

- The path exists. `vfor` does not report a missing path; it just finds no files.
- The files have an extension `vfor` handles for that operation. See [Tools and file types](tools.md).
- The files are not excluded. `node_modules/`, `dist/`, `build/`, `.venv/`, `*.min.js` and similar are excluded by default, and so is everything listed in `.gitignore`, `.vforignore`, the parent directory's `.gitignore` and `~/.vforignore_global`. `vfor ignore show <dir>` lists the ignore-file patterns.
- You did not pass `--exclude` as a plain string. See the next section.

### Every file is excluded after `--exclude "*.py"`

`--exclude` expects a list. A plain string is split into single characters, and the character `*` matches everything. Write the list in brackets:

```bash
vfor fmt src/ --exclude='["*.py"]'
```

## A file fails

### `No formatting tool available for .<ext>` or `No minification tool available for .<ext>`

None of the tools for that extension is installed, or the extension is not supported for that operation at all (for example, `.py` with `mini`). Install one of the tools listed in [Tools and file types](tools.md) and run `vfor tools` to confirm. If a tool you just installed still shows as missing, delete `~/.cache/vfor/tool_cache.json`.

### `All format tools failed - dprint: … No config file found`

`dprint` needs a `dprint.json`. Run `dprint init` in the project, or let `vfor install` write a starter file. Alternatively install a tool that comes earlier in the list for that extension (for TOML, `taplo`).

### `<tool> timed out after 30 seconds`

Each tool run is limited to 30 seconds. Very large files can hit this. Process them separately or with the tool directly.

### `Binary file detected`, `Empty file`, `File too large`

The file failed a pre-check and was left unchanged. See [Safety and backups](safety.md#what-is-skipped) for the list.

### `File is locked or permission denied`

`vfor` could not open the file for writing. Check the file's permissions and whether another program holds it open.

## Unexpected results

### A CSS file got bigger after `vfor mini`

Without `lightningcss`, CSS "minification" falls back to `biome format --write`, which formats rather than minifies. Install `lightningcss` (`npm install -g lightningcss-cli`) and run again.

### My `preferred_js_tool` setting is ignored

In this version the `preferred_*_tool` settings are read and shown by `vfor configure show`, but tool choice always follows the fixed order in [Tools and file types](tools.md). To use a different tool, uninstall the ones before it in the list, or call the tool directly.

### No `.vfor_backup` files were created

That is the current behaviour; see [Safety and backups](safety.md#backups-are-not-written-in-this-version). Use version control to undo changes.

### `vfor` stopped and asked `Do you want to continue? [y/N]`

The run touches 100 files or more, 50 MB or more, or a file of 50 MB or more. Answer `y`, or pass `--force`.

## Command-line errors

### `--help` after a command runs the command

Fire passes `--help` on to the command. Put `--` before it:

```bash
vfor mini -- --help
```

### `--no-backup` is not recognised

Fire's syntax for turning off a flag is `--no` followed by the flag name with no hyphen: `--nobackup`, `--norecursive`.

### `TypeError: … unexpected keyword argument 'exclude'` in Python

The Python keyword is `exclude_patterns`. See [Python API](python-api.md).
