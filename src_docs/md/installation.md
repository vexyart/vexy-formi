# Installation

`vexy-formi` has two parts: the Python package that provides `vfor`, and the external formatters and minifiers it runs. You need both.

## Requirements

- Python 3.10 or newer.
- At least one external tool for each file type you want to process. See [Tools and file types](tools.md).

The Python dependencies are `fire`, `rich`, `pathspec` and `chardet`; the installer pulls them in.

## Install the package

=== "uv"

    ```bash
    uv tool install vexy-formi
    ```

=== "pip"

    ```bash
    python -m pip install vexy-formi
    ```

Check that the command is on your `PATH`:

```bash
vfor tools
```

The result is a table of 13 tools with `✓ Available` or `✗ Missing` next to each, followed by a line such as `6/13 tools available`.

## Install the external tools

You can install the tools yourself with your usual package manager, or let `vfor install` do it.

### Option 1: install only what you need

Pick tools from [Tools and file types](tools.md). For example, to format Python and JSON:

```bash
brew install ruff jq
```

Run `vfor tools` again; the new tools show as available. `vfor` caches the result of its tool check for one hour in `~/.cache/vfor/tool_cache.json`. The cache is discarded early when `PATH`, `HOME`, `VIRTUAL_ENV` or `NODE_PATH` changes.

### Option 2: `vfor install`

`vfor install` installs a fixed set of tools. Read what it does before you run it; it changes your system and writes files into the current directory.

1. If Homebrew is missing on macOS or Linux, it runs the official Homebrew install script.
2. If `npm` is missing, it installs Node.js with Homebrew.
3. With Homebrew it installs `dprint`, `biome`, `esbuild`, `ruff`, `jq`, `yq` and `taplo`.
4. With `npm install -g` it installs `@swc/cli` and `@swc/core`, `terser`, `lightningcss-cli`, `prettier` and `html-minifier-terser`.
5. With `cargo` it installs `minhtml`, and with Homebrew `minify`.
6. In the current directory it creates `dprint.json`, `biome.json`, `ruff.toml` and `.vfor.json`, each only if the file does not exist yet.
7. It prints a summary table.

```bash
cd ~/my-project     # the config files land here
vfor install --verbose
```

### Updating the tools

`vfor update` runs `brew update`, `npm update -g npm` and `rustup update`, updates the tools it finds, cleans the package manager caches (`brew cleanup`, `npm cache clean --force`, `cargo cache --autoclean`) and checks each tool. If `dprint.json` exists in the current directory, it copies it to `dprint.json.backup.<timestamp>` and replaces its `plugins` list with pinned plugin versions.

## Install from source

```bash
git clone https://github.com/vexyart/vexy-formi.git
cd vexy-formi
uv pip install -e ".[dev,test]"
```

## Uninstall

=== "uv"

    ```bash
    uv tool uninstall vexy-formi
    ```

=== "pip"

    ```bash
    python -m pip uninstall vexy-formi
    ```

This removes `vfor` only. Tools installed by `vfor install` stay; remove them with Homebrew, `npm` or `cargo`. Remove `~/.cache/vfor/` to delete the tool cache and performance baselines.
