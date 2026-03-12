import os
import shutil
import tempfile
from pathlib import Path

import pandas as pd
from loguru import logger


def _flatten_errors(errors):
    flat = []
    for item in errors:
        if isinstance(item, list):
            flat.extend(item)
        else:
            flat.append(item)
    return flat


def _is_databricks() -> bool:
    return "DATABRICKS_RUNTIME_VERSION" in os.environ


def _is_volume_path(path: Path) -> bool:
    return str(path).replace("\\", "/").startswith("/Volumes/")


def _write_with_tmp(path: Path, write_fn) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_file = Path(tmpdir) / path.name
        write_fn(tmp_file)
        shutil.copy2(tmp_file, path)


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
    suffix = path.suffix.lower()

    def _do_write(target: Path) -> None:
        if suffix == ".parquet":
            df.to_parquet(target, index=False)
        elif suffix in {".xlsx", ".xls"}:
            df.to_excel(target, index=False)
        elif suffix == ".json":
            df.to_json(target, orient="records", lines=True)
        else:
            df.to_csv(target, index=False)

    try:
        if _is_databricks() and _is_volume_path(path) and suffix in {".xlsx", ".xls"}:
            _write_with_tmp(path, _do_write)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            _do_write(path)
    except Exception as exc:
        if suffix in {".xlsx", ".xls"}:
            fallback = path.with_suffix(".csv")
            logger.warning("Output Excel failed ({}). Fallback to {}", exc, fallback)
            _write_dataframe(df, fallback)
        else:
            raise


def _write_dataframe_list(dfs: list[pd.DataFrame], path: str | Path) -> None:
    path = Path(path)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        try:
            def _write_excel(target: Path) -> None:
                with pd.ExcelWriter(target) as writer:
                    for idx, df in enumerate(dfs):
                        df.to_excel(writer, sheet_name=_sheet_name(df, idx), index=False)

            if _is_databricks() and _is_volume_path(path):
                _write_with_tmp(path, _write_excel)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                _write_excel(path)
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


def write_delta_table(df_final: pd.DataFrame, table_name: str, write_mode: str) -> None:
    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    spark.createDataFrame(df_final).write.format("delta").mode(write_mode).option(
        "overwriteSchema", "true"
    ).saveAsTable(table_name)


def publish_outputs(result: dict, output_paths: dict) -> None:
    df_final = result["df_final"]
    qc_summary = pd.DataFrame(result["qc_summary"])
    errors_list = _flatten_errors(result["errors_list"])
    errors_df = pd.DataFrame(errors_list)
    df_to_analyze = result["df_to_analyze"]
    log_percentage = pd.DataFrame(result["log_percentage"])

    table_name = output_paths.get("table_name")
    write_mode = output_paths.get("write_mode", "overwrite")
    if table_name:
        write_delta_table(df_final, table_name, write_mode)

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
        report_path.write_text(
            pd.Series(report).to_json(),
            encoding="utf-8",
        )
