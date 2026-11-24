# Current work

- The Release workflow builds the tagged Python package and publishes to PyPI through OIDC. The development guide now documents that flow. The PyPI project owner needs to confirm the trusted publisher for `vexyart/vexy-formi`, `release.yml`, environment `pypi`.
- The site uses fly-january 0.2.1 with unbranded chrome. `./build.sh docs` rebuilt the 12 HTML pages without warnings after the release documentation changed.
- `actionlint .github/workflows/release.yml` and `bash -n publish.sh` passed. Pytest collected 74 tests, with 72 passing and two known failures. `test_format_support` expects a JavaScript minifier and `test_vfor_tools` expects an old table title.
- `PLAN.md` and `TODO.md` track the remaining test coverage, recovery, and configuration work. `CHANGELOG.md` records the verified items.
