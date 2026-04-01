# Pipeline Architecture

## Overview
The pipeline is split into explicit macromodules with clear inputs/outputs.
Domain components are placed under `domains/` and shared utilities under `common/`:

```
pipeline/
  orchestrator.py
  contracts.py
  stages/
    extraction.py
    reconstruction.py
    canonicalization.py
    publish.py
    refined/
      core.py
    load/
      delta.py
  domains/
    reconstruction/
    canonicalization/
  common/
  transforms/
```

Macromodules:
1. Extraction / Raw Acquisition
2. Table Reconstruction / Structural Parsing
3. Refined / Union / Data Quality
4. Load / Persistence / Reporting

The end-to-end orchestrator composes these stages without changing business logic.

## Module Contracts

### Module 1 — Extraction / Raw Acquisition
**Function:** `pipeline.stages.extraction.extract_raw`

**Input:**
- `config` (pipeline config dict)
- `project_root` (optional Path)

**Output:** `ExtractionOutput`
- `tables`: raw tables by page
- `page_config`: validated page config
- `extraction_cfg`: extraction config dict
- `raw_result`: full extractor result

### Module 2 — Table Reconstruction / Structural Parsing
**Function:** `pipeline.stages.reconstruction.reconstruct_tables`

**Input:**
- `tables`, `page_config`, `config`

**Output:** `ReconstructionOutput`
- `dfs_refined`: list of reconstructed tables
- `errors_list`: parsing errors

### Module 3 — Refined / Union / Data Quality
**Function:** `pipeline.stages.refined.canonicalize`

**Input:**
- `dfs_refined`, `errors_list`, `config`

**Output:** `CanonicalizationOutput`
- `df_final`
- `qc_summary`
- `errors_list`
- `df_to_analyze`
- `log_percentage`

### Module 4 — Publish / Persistence / Reporting
**Function:** `pipeline.stages.load.publish_outputs`

**Input:**
- `result` (dict from canonicalization)
- `output_paths` (resolved output config)

**Output:**
- Delta table write (if `table_name` is defined)
- QC/monitoring artifacts (if paths are defined)

## Orchestrator
**Function:** `pipeline.orchestrator.run_pipeline`

Responsibilities:
- reads config
- runs modules in sequence
- optionally publishes outputs

## Databricks Task Orchestration (future)
Each module can be run as a separate task in Databricks Jobs UI by invoking the stage
function with the appropriate input contract. The orchestrator remains the default
entrypoint for end-to-end execution.

## Guardrails
Architecture check:
- `python scripts/check_architecture.py`

Regression check:
- `python scripts/regression_check.py --config configs/pipeline/pipeline_config_DEC.json --write-baseline`
- `python scripts/regression_check.py --config configs/pipeline/pipeline_config_DEC.json`

Smoke run:
- `python scripts/smoke_run.py --config configs/pipeline/pipeline_config_DEC.json`

Publish check (local artifacts):
- `python scripts/publish_check.py --config configs/pipeline/pipeline_config_DEC.json --output-dir artifacts/publish --skip-delta`

## Root Compatibility Policy
The root `src/pipeline` is intentionally minimal. It may contain only:
- entrypoint/orchestration
- contracts

No business logic should be added in root. Domain logic must live in `domains/`,
`stages/`, `transforms/`, or `common/`. The architecture check enforces that root
modules (excluding explicitly allowed entrypoints) remain shim-only if any are added.

## Compatibility Shims
For backwards compatibility, the old flat stage modules remain available:
- `pipeline.stages.canonicalization` -> shim verso `pipeline.stages.refined`
- `pipeline.stages.publish` -> shim verso `pipeline.stages.load`
