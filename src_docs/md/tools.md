# Tools and file types

`vfor` does not format or minify anything itself. For every file it looks up the extension in a fixed, ordered list of external tools and runs the first one that is installed. The lists are defined in `ToolManager._setup_tool_commands()` in `src/vexy_formi/tools.py`.

## How a tool is chosen

1. Take the file's extension in lower case, for example `.js`.
2. Walk the list for that extension and operation from top to bottom.
3. Skip tools that are not installed. A tool counts as installed when `which <tool>` (`where` on Windows) finds it, or when `<tool> --version` exits with `0`.
4. Run the first installed tool on the file.
5. If it fails, run the next installed tool in the list. If every tool fails, the file fails with `All <operation> tools failed - ` followed by each tool's error.

A tool that exits with an error whose message suggests a temporary problem (for example `resource temporarily unavailable` or `device busy`) is retried up to two more times. Each tool run has a 30-second time limit.

The order is fixed. The `preferred_*_tool` settings in [Configuration](configuration.md) are read but do not change it in this version.

## Format

`vfor fmt` handles these extensions. `{file}` is the file being processed; every command rewrites it in place.

| Extension | Tools, in order of preference | Command |
| --- | --- | --- |
| `.py` | `ruff`, `black` | `ruff format {file}` · `black {file}` |
| `.js`, `.ts` | `biome`, `prettier`, `dprint` | `biome format --write {file}` · `prettier --write {file}` · `dprint fmt {file}` |
| `.jsx`, `.tsx` | `biome`, `prettier` | as above |
| `.css`, `.scss` | `biome`, `prettier` | as above |
| `.html` | `prettier`, `biome` | as above |
| `.json` | `biome`, `prettier`, `jq` | as above · `jq . {file}` |
| `.toml` | `taplo`, `dprint` | `taplo fmt {file}` · `dprint fmt {file}` |
| `.yaml`, `.yml` | `prettier`, `yq` | `prettier --write {file}` · `yq -i e . {file}` |
| `.md` | `dprint`, `prettier` | `dprint fmt {file}` · `prettier --write {file}` |

`.htm` and `.jsonc` are not formatted.

## Minify

`vfor mini` handles these extensions.

| Extension | Tools, in order of preference | Command |
| --- | --- | --- |
| `.js` | `esbuild`, `swc`, `terser` | `esbuild {file} --minify --outfile={file}` · `swc {file} --minify -o {file}` · `terser {file} -c -m -o {file}` |
| `.ts`, `.jsx`, `.tsx` | `esbuild`, `swc` | as above |
| `.css` | `lightningcss`, `biome` | `lightningcss {file} -o {file} --minify` · `biome format {file} --write` |
| `.scss` | `lightningcss` | as above |
| `.html`, `.htm` | `html-minifier-terser` | `html-minifier-terser {file} -o {file} --collapse-whitespace --remove-comments` |
| `.json` | `jq` | `jq -c . {file}`, output written back to the file |
| `.jsonc` | `biome` | `biome format {file} --write` |

Two entries are not real minifiers. For `.css` without `lightningcss`, and for `.jsonc`, the tool is `biome format`, which reformats the file and may make it larger.

Python, Markdown, TOML and YAML files are never minified.

## The tool list in `vfor tools`

| Tool | Type | Written in | Formats |
| --- | --- | --- | --- |
| `esbuild` | minifier | Go | JS, TS |
| `swc` | minifier | Rust | JS, TS |
| `biome` | formatter | Rust | JS, TS, JSON, CSS |
| `ruff` | formatter | Rust | Python |
| `lightningcss` | minifier | Rust | CSS |
| `taplo` | formatter | Rust | TOML |
| `dprint` | formatter | Rust | Multiple |
| `terser` | minifier | Node.js | JS |
| `prettier` | formatter | Node.js | Multiple |
| `black` | formatter | Python | Python |
| `jq` | processor | C | JSON |
| `yq` | processor | Go | YAML |
| `html-minifier-terser` | minifier | Node.js | HTML |

## Tool settings

`vfor` passes no settings of its own to the tools; the commands above are run exactly as shown, from the directory where you started `vfor`. Each tool finds and reads its own configuration files the way it normally does.

`dprint` refuses to run without a configuration file. `vfor install` writes a starter `dprint.json` into the current directory; you can also run `dprint init`.

## The tool cache

Each tool check starts a subprocess, so `vfor` caches the results in `~/.cache/vfor/tool_cache.json`:

- The cache is valid for one hour.
- It is discarded early when `PATH`, `HOME`, `VIRTUAL_ENV` or `NODE_PATH` changes.
- On a cache miss, only `ruff`, `biome`, `prettier`, `black` and `esbuild` are checked at once; other tools are checked the first time a file needs them.
- If a tool disappears between the check and the run, it is marked unavailable in the cache.

Delete the file to force a fresh check.
