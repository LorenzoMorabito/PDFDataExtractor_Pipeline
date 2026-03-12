import argparse
import json
import sys
from pathlib import Path

from loguru import logger


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish-stage check for PDFDataExtractor pipeline.")
    parser.add_argument(
        "--config",
        default="configs/pipeline/pipeline_config_DEC.json",
        help="Pipeline config path (JSON).",
    )
    parser.add_argument(
        "--output-dir",
        default="artifacts/publish",
        help="Output directory for publish artifacts.",
    )
    parser.add_argument(
        "--skip-delta",
        action="store_true",
        help="Skip Delta table write (useful outside Databricks).",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    project_root = _project_root()

    config_path = _resolve_path(project_root, args.config)
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    output_cfg = config.get("output", {})
    output_dir = _resolve_path(project_root, args.output_dir)

    output_paths = {
        "df_final": output_dir / "df_final.csv",
        "qc_summary": output_dir / "qc_summary.csv",
        "errors": output_dir / "errors.csv",
        "df_to_analyze": output_dir / "df_to_analyze.xlsx",
        "log_percentage": output_dir / "log_percentage.csv",
        "run_report": output_dir / "run_report.json",
        "table_name": None if args.skip_delta else output_cfg.get("table_name"),
        "write_mode": output_cfg.get("write_mode", "overwrite"),
    }

    sys.path.insert(0, str(project_root / "src"))
    from pipeline.orchestrator import run_pipeline
    from pipeline.stages.publish import publish_outputs

    result = run_pipeline(config, project_root=project_root, publish=False)

    try:
        publish_outputs(result, output_paths)
        logger.info("Publish check completed. Delta write attempted: {}", bool(output_paths.get("table_name")))
    except ModuleNotFoundError as exc:
        if "pyspark" in str(exc):
            logger.warning("pyspark not available. Skipping Delta write and publishing file artifacts only.")
            output_paths["table_name"] = None
            publish_outputs(result, output_paths)
        else:
            raise

    logger.info("Publish artifacts written to {}", output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
