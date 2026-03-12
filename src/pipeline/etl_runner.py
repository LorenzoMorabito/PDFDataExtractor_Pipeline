from pathlib import Path

from .orchestrator import run_pipeline as _run_pipeline


def run_pipeline(config: dict, project_root: Path | None = None):
    return _run_pipeline(config, project_root=project_root, publish=False)
