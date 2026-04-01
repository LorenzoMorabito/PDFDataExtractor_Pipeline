import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd
from loguru import logger

PROJECT_ROOT = None


def _project_root() -> Path:
    if "__file__" in globals():
        return Path(__file__).resolve().parent
    return Path.cwd()


PROJECT_ROOT = _project_root()
sys.path.insert(0, str(PROJECT_ROOT / "src"))
pd.set_option("future.no_silent_downcasting", True)

from pipeline.orchestrator import run_pipeline as _run_pipeline


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def _build_output_paths(
    project_root: Path,
    config: dict,
    extraction_cfg: dict,
    config_path: Path,
    output_dir: str | None,
) -> dict:
    output_cfg = config.get("output", {})
    paths = {
        "df_refined": output_cfg.get("df_refined_path"),
        "df_final": output_cfg.get("df_final_path"),
        "qc_summary": output_cfg.get("qc_summary_path"),
        "errors": output_cfg.get("errors_path"),
        "df_to_analyze": output_cfg.get("df_to_analyze_path"),
        "log_percentage": output_cfg.get("log_percentage_path"),
        "run_report": output_cfg.get("run_report_path"),
        "table_name": output_cfg.get("table_name"),
        "write_mode": output_cfg.get("write_mode", "overwrite"),
        "key_columns": output_cfg.get("key_columns", ["record_hash"]),
        "partition_by": output_cfg.get("partition_by", []),
        "column_mapping": output_cfg.get("column_mapping", {}),
        "required_columns": output_cfg.get("required_columns", []),
        "default_values": output_cfg.get("default_values", {}),
    }

    if not paths["df_final"]:
        paths["df_final"] = extraction_cfg.get("output_excel")

    tag = config_path.stem.replace("pipeline_config_", "")
    if output_dir:
        base = _resolve_path(project_root, output_dir)
        paths["df_refined"] = str(base / f"df_refined_{tag}.csv")
        paths["df_final"] = str(base / f"df_final_{tag}.csv")
        paths["qc_summary"] = str(base / f"qc_summary_{tag}.csv")
        paths["errors"] = str(base / f"errors_{tag}.csv")
        paths["df_to_analyze"] = str(base / f"df_to_analyze_{tag}.xlsx")
        paths["log_percentage"] = str(base / f"log_percentage_{tag}.csv")
        paths["run_report"] = str(base / f"run_report_{tag}.json")

    for key in ("df_refined", "df_final", "qc_summary", "errors", "df_to_analyze", "log_percentage", "run_report"):
        if paths.get(key):
            paths[key] = _resolve_path(project_root, paths[key])

    return paths


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PDFDataExtractor pipeline.")
    parser.add_argument(
        "--config",
        default=os.getenv("PIPELINE_CONFIG", "configs/pipeline/pipeline_config_DEC.json"),
        help="Pipeline config path (JSON).",
    )
    parser.add_argument(
        "--output-dir",
        default=os.getenv("PIPELINE_OUTPUT_DIR"),
        help="Override output directory for artifacts.",
    )
    parser.add_argument(
        "--log-level",
        default=os.getenv("LOG_LEVEL", "INFO"),
        help="Log level (e.g., INFO, DEBUG).",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Run pipeline without writing output artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    logger.remove()
    logger.add(sys.stderr, level=str(args.log_level).upper())

    config_path = _resolve_path(PROJECT_ROOT, args.config)
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    extraction_cfg_path = _resolve_path(PROJECT_ROOT, config["extraction_config_path"])
    with extraction_cfg_path.open("r", encoding="utf-8") as f:
        extraction_cfg = json.load(f)

    output_paths = _build_output_paths(PROJECT_ROOT, config, extraction_cfg, config_path, args.output_dir)
    result = _run_pipeline(
        config,
        project_root=PROJECT_ROOT,
        output_paths=output_paths,
        publish=not args.no_write,
    )

    logger.info(
        "Pipeline completata. DF refined shape={} | DF finale legacy shape={}",
        result["df_refined"].shape,
        result["df_final"].shape,
    )
    return 0


if __name__ == "__main__":
    main()
