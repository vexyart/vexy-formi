# Development

## Repository layout

| Path | Content |
| --- | --- |
| `src/vexy_formi/cli.py` | The `VFor` class behind `vfor` |
| `src/vexy_formi/core.py` | `FileProcessor`, batch processing, results |
| `src/vexy_formi/tools.py` | `ToolManager`: tool lists, detection, execution |
| `src/vexy_formi/files.py` | `FileHandler`: file discovery, exclusions, validation |
| `src/vexy_formi/config.py` | Settings from defaults, JSON files and environment |
| `src/vexy_formi/safety.py` | Risk rating and the confirmation prompt |
| `src/vexy_formi/performance.py` | Baselines for `perf_check` |
| `src/vexy_formi/tools_install.py`, `tools_update.py` | `vfor install` and `vfor update` |
| `tests/` | pytest suite; `tests/fixtures/` holds one sample file per type |
| `testdata/` | Larger JSON samples (about 11 MB), not shipped in the package |
| `src_docs/` | Documentation source (this site) |
| `docs/` | The built site, served by GitHub Pages |

## Set up an environment

```bash
git clone https://github.com/vexyart/vexy-formi.git
cd vexy-formi
uv venv
uv pip install -e ".[dev,test]"
```

## Run the tests

```bash
uv run python -m pytest -q -o addopts="" -n auto
```

The tests copy the fixtures into temporary directories before processing them, so the repository is not modified. Some tests depend on which external tools are installed. On a machine with `biome`, `dprint`, `ruff`, `yq`, `black` and `jq` but no `esbuild`, two tests failed (`test_format_support`, `test_vfor_tools`) and 72 passed.

## Lint and format

```bash
uvx ruff check src tests
uvx ruff format --respect-gitignore src tests
```

The `pre-commit` configuration runs Ruff and a set of whitespace and file checks.

## Versioning

The version comes from git tags (`vX.Y.Z`) through `hatch-vcs`. At build time it is written to `src/vexy_formi/__version__.py`, which is not tracked in git. Between tags it looks like `1.0.5.dev0+gf3cc63237`. Without a build, `vexy_formi.__version__` falls back to the installed distribution's metadata, then to `0.0.0`.

## Build

```bash
./build.sh            # docs and package
./build.sh docs       # src_docs/ → docs/
./build.sh package    # dist/*.whl and dist/*.tar.gz, checked with twine
```

The source distribution contains the package, `tests/`, `README.md`, `CHANGELOG.md`, `LICENSE` and `pyproject.toml`. The wheel contains the package only.

## Documentation

Sources are in `src_docs/md/`, the configuration in `src_docs/mkdocs.yml`. The site is built with ProperDocs and the MaterialX theme.

```bash
src_docs/build.sh          # strict build into docs/
src_docs/build.sh serve    # live preview on http://127.0.0.1:8000
```

The `Docs` workflow rebuilds `docs/` on each push to `main` that touches `src_docs/`.

## Release

1. Export a PyPI token for `uv publish`, for example `UV_PUBLISH_TOKEN`.
2. Run:

    ```bash
    ./publish.sh
    ```

    `gitnextver` commits pending changes, tags the next `vX.Y.Z` and pushes. The script then builds from that tag and uploads with `uv publish`.

The pushed tag also triggers the `Release` workflow, which builds the package, uploads it to PyPI with `skip-existing` (so the upload from `publish.sh` does not make it fail) and creates a GitHub release.
