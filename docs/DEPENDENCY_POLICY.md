# Dependency Policy

## Ownership
### Library (pdfdataextractor)
Owns:
- pyproject.toml
- package dependencies
- wheel versioning

### Pipeline
Owns:
- run_pipeline.py
- pipeline configs
- databricks.yml
- orchestration logic
- local development requirements.txt

### Databricks job
Owns:
- runtime target
- wheel reference
- extra dependencies only if NOT already included in the wheel

## Rules
1. The wheel is the single source of truth for library dependencies.
2. databricks.yml must not repeat package dependencies already declared by the wheel.
3. requirements.txt is for local development only and must not become a second source of truth for runtime dependencies.
4. ABI-sensitive dependencies (for example numpy) must be pinned conservatively against the Databricks target runtime.
