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
        default="configs/pipeline/pipeline_config_DEC.local.sample.json",
        help="Pipeline config path (JSON). Default: local shared sample config.",
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


def _file_ok(path: Path) -> bool:
    return path.exists() and path.is_file() and path.stat().st_size > 0


def _dir_with_csv(path: Path) -> bool:
    if not path.exists() or not path.is_dir():
        return False
    return any(p.is_file() and p.suffix.lower() == ".csv" and p.stat().st_size > 0 for p in path.iterdir())


def main() -> int:
    args = _parse_args()
    project_root = _project_root()

    config_path = _resolve_path(project_root, args.config)
    with config_path.open("r", encoding="utf-8") as f:
        config = json.load(f)

    output_cfg = config.get("output", {})
    output_dir = _resolve_path(project_root, args.output_dir)

    output_paths = {
        "df_refined": output_dir / "df_refined.csv",
        "df_final": output_dir / "df_final.csv",
        "qc_summary": output_dir / "qc_summary.csv",
        "errors": output_dir / "errors.csv",
        "df_to_analyze": output_dir / "df_to_analyze.xlsx",
        "log_percentage": output_dir / "log_percentage.csv",
        "run_report": output_dir / "run_report.json",
        "table_name": None if args.skip_delta else output_cfg.get("table_name"),
        "write_mode": output_cfg.get("write_mode", "overwrite"),
        "key_columns": output_cfg.get("key_columns", ["record_hash"]),
        "partition_by": output_cfg.get("partition_by", []),
        "column_mapping": output_cfg.get("column_mapping", {}),
        "required_columns": output_cfg.get("required_columns", []),
        "default_values": output_cfg.get("default_values", {}),
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

    expected = {
        "df_refined.csv": output_dir / "df_refined.csv",
        "df_final.csv": output_dir / "df_final.csv",
        "qc_summary.csv": output_dir / "qc_summary.csv",
        "errors.csv": output_dir / "errors.csv",
        "log_percentage.csv": output_dir / "log_percentage.csv",
        "run_report.json": output_dir / "run_report.json",
        "df_to_analyze.xlsx_or_dir": output_dir / "df_to_analyze.xlsx",
    }

    results = {}
    for name, path in expected.items():
        if name.endswith("xlsx_or_dir"):
            ok = _file_ok(path) or _dir_with_csv(path.with_suffix(""))
        else:
            ok = _file_ok(path)
        results[name] = {
            "path": str(path),
            "ok": bool(ok),
            "size": int(path.stat().st_size) if path.exists() and path.is_file() else 0,
        }

    report = {
        "delta_attempted": bool(output_paths.get("table_name")),
        "output_dir": str(output_dir),
        "files": results,
    }
    report_path = output_dir / "publish_check_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    missing = [name for name, info in results.items() if not info["ok"]]
    if missing:
        logger.error("Publish check failed. Missing/empty artifacts: {}", missing)
        return 1

    logger.info("Publish artifacts written to {}", output_dir)
    logger.info("Publish check report: {}", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
