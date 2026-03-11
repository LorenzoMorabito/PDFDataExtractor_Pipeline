# Runtime Target

## Official runtime
- Platform: Databricks Serverless Jobs
- Environment version: 2
- Python: 3.11.x
- Deployment source of truth: databricks.yml

## Why this is the target
The deployed job is configured in databricks.yml with serverless environment version 2.
All package builds, local tests, and bundle deployments must stay compatible with this runtime.

## Rules
1. The library wheel must be compatible with Python 3.11.
2. Core dependencies must not be duplicated between wheel metadata and job environment.
3. Any library implementation/dependency change requires:
   - version bump
   - new wheel build
   - new wheel upload
   - bundle update
4. Local development must use a dedicated Python 3.11 virtual environment.
5. Canonical output is Delta table; file artifacts are for QC/monitoring only.

## Local environments
- .build_venv = package build only
- .venv311-dev = runtime-compatible local development (Python 3.11)
