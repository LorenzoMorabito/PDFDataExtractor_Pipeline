# Refactor Validation Report

Date: 2026-03-12
Branch: refactor/pipeline-modularization

## Baseline (main)
Baseline generated on `main` from stable sample input and saved as `artifacts/baseline_main.json`.

Summary:
- df_final shape: [1919, 21]
- df_final hash: 8695901827336216103
- qc_summary shape: [138, 13]
- qc_summary hash: 12848070848576579044
- errors_list shape: [1, 3]
- errors_list hash: 11858281609702309818

## Checks Executed (refactor)

1) Architecture boundaries
Command:
- `python scripts/check_architecture.py`
Result: PASS

2) Regression check vs main baseline
Command:
- `python scripts/regression_check.py --config artifacts/_baseline_config_DEC.json --baseline artifacts/baseline_main.json`
Result: PASS

3) Smoke run (end-to-end without publish)
Command:
- `python scripts/smoke_run.py --config artifacts/_baseline_config_DEC.json`
Result: PASS
- df_final shape: (1919, 23)

4) Publish check
Command:
- `python scripts/publish_check.py --config artifacts/_baseline_config_DEC.json --output-dir artifacts/publish --skip-delta`
Result: PASS (file artifacts written)
Note: Delta write skipped locally because pyspark is not available. Execute this check in Databricks without `--skip-delta` to validate Delta persistence.

## Legacy Shim Status
See `docs/REFACTOR_NOTES.md` for the list of shim/wrapper modules and their purpose.

## Notes
- Baseline config overrides the extraction config to use a local sample file (to avoid `/Volumes/...` paths).
- Hashes ignore non-functional fields (`run_id`, `timestamp_utc`) to prevent false positives.
