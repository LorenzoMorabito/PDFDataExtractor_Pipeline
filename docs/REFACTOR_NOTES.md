# Refactor Notes

## Legacy Modules Moved
Moved to domain folders:
- `HeaderProcessor.py` -> `domains/reconstruction/`
- `TableSlicer.py` -> `domains/reconstruction/`
- `TableSplitter.py` -> `domains/reconstruction/`
- `TitleExtractor.py` -> `domains/reconstruction/`
- `DataQuality.py` -> `domains/canonicalization/`
- `StartDate.py` -> `common/`
- `utilities.py` -> `common/`

## Shims / Wrappers
Legacy files in `src/pipeline/` are now thin wrappers that re-export the
new module locations to preserve backward compatibility.

## Guardrails
- Architecture check: `python scripts/check_architecture.py`
- Regression harness: `python scripts/regression_check.py`
- Smoke run: `python scripts/smoke_run.py`

## Root File Classification
| File | Type | Status | Notes |
| --- | --- | --- | --- |
| `__init__.py` | entrypoint | keep | Package exports only |
| `contracts.py` | contract | keep | IO contracts between stages |
| `orchestrator.py` | entrypoint | keep | End-to-end orchestration |
| `etl_runner.py` | shim | keep | Legacy wrapper for orchestrator |
| `etl_steps.py` | shim | keep | Legacy re-export for transforms |
| `etl_steps_deprecated.py` | deprecated | keep (temporary) | Re-export legacy transforms for compatibility |
| `DataQuality.py` | shim | keep | Re-export canonicalization DataQuality |
| `HeaderProcessor.py` | shim | keep | Re-export reconstruction HeaderProcessor |
| `TableSlicer.py` | shim | keep | Re-export reconstruction TableSlicer |
| `TableSplitter.py` | shim | keep | Re-export reconstruction TableSplitter |
| `TitleExtractor.py` | shim | keep | Re-export reconstruction TitleExtractor |
| `StartDate.py` | shim | keep | Re-export common StartDate |
| `utilities.py` | shim | keep | Re-export common utilities |
