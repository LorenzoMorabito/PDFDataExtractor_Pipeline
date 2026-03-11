import argparse
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


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def _flatten_errors(errors):
    flat = []
    for item in errors:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    return flat


def _sheet_name(df: pd.DataFrame, idx: int) -> str:
    base = f"table_{idx:03d}"
    if "page_num" in df.columns:
        try:
            page = int(pd.to_numeric(df["page_num"].dropna().iloc[0]))
            base = f"page_{page:03d}_{idx:03d}"
        except Exception:
            pass
    return base[:31]


def _write_dataframe(df: pd.DataFrame, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    try:
        if suffix == ".parquet":
            df.to_parquet(path, index=False)
        elif suffix in {".xlsx", ".xls"}:
            df.to_excel(path, index=False)
        elif suffix == ".json":
            df.to_json(path, orient="records", lines=True)
        else:
            df.to_csv(path, index=False)
    except Exception as exc:
        if suffix in {".xlsx", ".xls"}:
            fallback = path.with_suffix(".csv")
            logger.warning("Output Excel failed ({}). Fallback to {}", exc, fallback)
            df.to_csv(fallback, index=False)
        else:
            raise


def _write_dataframe_list(dfs: list[pd.DataFrame], path: str | Path) -> None:
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with pd.ExcelWriter(path) as writer:
                for idx, df in enumerate(dfs):
                    df.to_excel(writer, sheet_name=_sheet_name(df, idx), index=False)
            return
        except Exception as exc:
            logger.warning("Output Excel failed ({}). Fallback to CSV directory.", exc)
            path = path.with_suffix("")

    out_dir = path if not path.suffix else path.with_suffix("")
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, df in enumerate(dfs):
        name = f"df_{idx:03d}.csv"
        if "page_num" in df.columns:
            try:
                page = int(pd.to_numeric(df["page_num"].dropna().iloc[0]))
                name = f"page_{page:03d}_{idx:03d}.csv"
            except Exception:
                pass
        df.to_csv(out_dir / name, index=False)


def _build_output_paths(
    config: dict,
    extraction_cfg: dict,
    config_path: Path,
    output_dir: str | None,
) -> dict:
    output_cfg = config.get("output", {})
    paths = {
        "df_final": output_cfg.get("df_final_path"),
        "qc_summary": output_cfg.get("qc_summary_path"),
        "errors": output_cfg.get("errors_path"),
        "df_to_analyze": output_cfg.get("df_to_analyze_path"),
        "log_percentage": output_cfg.get("log_percentage_path"),
        "run_report": output_cfg.get("run_report_path"),
    }

    if not paths["df_final"]:
        paths["df_final"] = extraction_cfg.get("output_excel")

    tag = config_path.stem.replace("pipeline_config_", "")
    if output_dir:
        base = Path(output_dir)
        paths["df_final"] = str(base / f"df_final_{tag}.csv")
        paths["qc_summary"] = str(base / f"qc_summary_{tag}.csv")
        paths["errors"] = str(base / f"errors_{tag}.csv")
        paths["df_to_analyze"] = str(base / f"df_to_analyze_{tag}.xlsx")
        paths["log_percentage"] = str(base / f"log_percentage_{tag}.csv")
        paths["run_report"] = str(base / f"run_report_{tag}.json")

    return paths


def _write_outputs(result: dict, output_paths: dict) -> None:
    df_final = result["df_final"]
    qc_summary = pd.DataFrame(result["qc_summary"])
    errors_list = _flatten_errors(result["errors_list"])
    errors_df = pd.DataFrame(errors_list)
    df_to_analyze = result["df_to_analyze"]
    log_percentage = pd.DataFrame(result["log_percentage"])

    if output_paths.get("df_final"):
        _write_dataframe(df_final, output_paths["df_final"])
    if output_paths.get("qc_summary"):
        _write_dataframe(qc_summary, output_paths["qc_summary"])
    if output_paths.get("errors"):
        _write_dataframe(errors_df, output_paths["errors"])
    if output_paths.get("df_to_analyze"):
        _write_dataframe_list(df_to_analyze, output_paths["df_to_analyze"])
    if output_paths.get("log_percentage"):
        _write_dataframe(log_percentage, output_paths["log_percentage"])
    if output_paths.get("run_report"):
        report_path = Path(output_paths["run_report"])
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report = {
            "df_final_shape": list(df_final.shape),
            "qc_summary_rows": int(len(qc_summary)),
            "errors_rows": int(len(errors_df)),
            "df_to_analyze_count": int(len(df_to_analyze)),
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")


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

    result = run_pipeline(config, project_root=PROJECT_ROOT)
    df_final = result["df_final"]

    output_paths = _build_output_paths(config, extraction_cfg, config_path, args.output_dir)
    if not args.no_write:
        _write_outputs(result, output_paths)

    logger.info("Pipeline completata. DF finale shape={}", df_final.shape)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
