# Refactor Validation Report

Date: 2026-03-12
Branch: refactor/pipeline-modularization

## Baseline (main)
Baseline generated on `main` from stable sample input and saved as `artifacts/baseline_main.json`.

Main commit (baseline): a5d90aca98694324593ea61b115f27858e48a52a
Refactor commit (validated): 75c9f9180b2871ccf77780c6bcb554de9d1cbbf7
Config used: `artifacts/_baseline_config_DEC.json`
Ignored non-functional fields: `run_id`, `timestamp_utc`

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

4) Publish check (local artifacts)
Command:
- `python scripts/publish_check.py --config artifacts/_baseline_config_DEC.json --output-dir artifacts/publish --skip-delta`
Result: PASS
Delta write: SKIPPED (out of scope local; requires Databricks/pyspark)

Artifacts produced (local):
- `df_final.csv` (398987 bytes)
- `qc_summary.csv` (5241 bytes)
- `errors.csv` (72 bytes)
- `log_percentage.csv` (126 bytes)
- `run_report.json` (90 bytes)
- `df_to_analyze.xlsx` (4937 bytes)

Publish check report:
- `artifacts/publish/publish_check_report.json`

## Legacy Shim Status
See `docs/REFACTOR_NOTES.md` for the list of shim/wrapper modules and their purpose.

## Notes
- Baseline config overrides the extraction config to use a local sample file (to avoid `/Volumes/...` paths).
- Hashes ignore non-functional fields (`run_id`, `timestamp_utc`) to prevent false positives.
