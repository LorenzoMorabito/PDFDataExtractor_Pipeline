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
