# VexyFormi plan

## Test coverage

- **Strengthen the CLI tests for `--force` and `--dry-run`.** Run both flags on a batch that triggers a safety prompt. Assert that `--force` succeeds without input and that `--dry-run` leaves the files byte-for-byte unchanged.
- **Cover large-file handling and memory use.** Exercise files near and above the configured size limit and measure peak memory.

## Error recovery

- **Handle disk-space exhaustion during backup creation.** Inject `ENOSPC` at backup creation and check that the original file stays intact and the CLI reports the failure.
- **Support resuming interrupted batches.** Interrupt a batch after a file completes, then verify that a resumed run processes the remaining files and preserves completed output.
- **Refresh the tool cache after a tool is installed or updated.** Warm the cache, change an installed tool without changing `PATH`, and check that the next operation detects the change.
- **Handle concurrent writes to the same file.** Run two CLI processes against one fixture and check that the result is complete and that a conflict is reported when appropriate.

## Configuration

- **Report invalid `.vfor.json` settings with actionable messages.** Try malformed JSON and an invalid setting value. Check that each diagnostic names the file and identifies the problem.
- **Choose defaults based on project type.** Compare defaults with and without `package.json` or `pyproject.toml` and verify that explicit settings still take precedence.
- **Support an explicit configuration file via `--config`.** Pass a fixture configuration to the CLI and check that it is loaded even when another project configuration is present.
