#EntryPoint

import json
import os
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
pd.set_option("future.no_silent_downcasting", True)

from pipeline.etl_runner import run_pipeline

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.remove()
logger.add(sys.stderr, level=log_level)

config_path = PROJECT_ROOT / "configs" / "pipeline" / "pipeline_config_DEC.json"
with config_path.open("r", encoding="utf-8") as f:
    config = json.load(f)

result = run_pipeline(config, project_root=PROJECT_ROOT)

df_final = result["df_final"]
qc_summary = result["qc_summary"]
errors_list = result["errors_list"]
df_to_analyze = result["df_to_analyze"]
log_percentage = result["log_percentage"]

logger.info("Pipeline completata. DF finale shape={}", df_final.shape)
