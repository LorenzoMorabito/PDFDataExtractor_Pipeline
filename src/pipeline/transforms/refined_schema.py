import calendar
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
from pandas.api.types import is_datetime64_any_dtype

from ..common.StartDate import MONTHS


def _resolve_source_path(project_root: Path | None, source_file_path: str | Path | None) -> Path | None:
    if source_file_path is None:
        return None
    path = Path(source_file_path)
    if path.is_absolute():
        return path.resolve()
    if project_root is None:
        return path
    return (project_root / path).resolve()


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.exists() or not path.is_file():
        return None
    return _sha256_bytes(path.read_bytes())


def _config_sha256(config: dict) -> str:
    raw = json.dumps(config, sort_keys=True, ensure_ascii=True).encode("utf-8")
    return _sha256_bytes(raw)


def _safe_series(df: pd.DataFrame, column_name: str):
    if column_name in df.columns:
        return df[column_name]
    return pd.Series(pd.NA, index=df.index)


def _infer_report_month(df: pd.DataFrame) -> int | None:
    months = []
    for value in df.get("period_agg", pd.Series(dtype="object")).dropna().unique():
        token = re.split(r"[\s,/_-]+", str(value).strip())[0].lower()
        month = MONTHS.get(token)
        if month is not None:
            months.append(month)

    if months:
        return max(months)

    if "period_start" not in df.columns:
        return None

    period_start = pd.to_datetime(df["period_start"], errors="coerce")
    valid_months = period_start.dropna().dt.month
    if valid_months.empty:
        return None
    return int(valid_months.max())


def _period_label(report_month: int | None, report_year: int) -> str:
    if report_month is None:
        return f"UNKNOWN_{report_year}"
    return f"{calendar.month_abbr[report_month].upper()}_{report_year}"


def _build_record_hash(df: pd.DataFrame) -> pd.Series:
    stable_columns = [
        "page_num",
        "table_id",
        "capitolo",
        "sottocapitolo",
        "page_title",
        "page_subtitle",
        "page_subtitle_1",
        "period_agg",
        "period_desc",
        "period_start",
        "item_agg_2",
        "item_agg_1",
        "item_agg",
        "py_year",
        "act_year",
        "bdg_year",
        "py_value",
        "act_value",
        "bdg_value",
        "var_vs_py_abs",
        "var_vs_py_pct",
        "var_vs_bdg_abs",
        "var_vs_bdg_pct",
        "delta_abs",
        "delta_pct",
        "report_year",
        "report_month",
        "report_period_label",
        "source_file_hash",
    ]
    tmp = df[stable_columns].copy()
    for column_name in tmp.columns:
        if is_datetime64_any_dtype(tmp[column_name]):
            tmp[column_name] = tmp[column_name].dt.strftime("%Y-%m-%d %H:%M:%S")
    tmp = tmp.fillna("<NA>")
    return pd.util.hash_pandas_object(tmp, index=False).astype("uint64").astype(str)


def build_refined_dataframe(
    df: pd.DataFrame,
    *,
    year_ref: int,
    config: dict,
    source_file_path: str | Path | None,
    project_root: Path | None = None,
    schema_version: str = "refined_wide_v1",
) -> pd.DataFrame:
    df = df.copy()

    source_path = _resolve_source_path(project_root, source_file_path)
    report_month = _infer_report_month(df)
    report_year = int(year_ref)

    py_col = f"{year_ref - 1}_act"
    act_col = f"{year_ref}_act"
    bdg_col = f"{year_ref}_bdg"

    df["py_year"] = year_ref - 1
    df["act_year"] = year_ref
    df["bdg_year"] = year_ref
    df["py_value"] = _safe_series(df, py_col)
    df["act_value"] = _safe_series(df, act_col)
    df["bdg_value"] = _safe_series(df, bdg_col)
    df["var_vs_py_abs"] = _safe_series(df, "eur_vs_act")
    df["var_vs_py_pct"] = _safe_series(df, "pct_vs_act")
    df["var_vs_bdg_abs"] = _safe_series(df, "eur_vs_bdg")
    df["var_vs_bdg_pct"] = _safe_series(df, "pct_vs_bdg")
    df["delta_abs"] = _safe_series(df, "eur_delta")
    df["delta_pct"] = _safe_series(df, "pct_delta")

    df["report_year"] = report_year
    df["report_month"] = report_month
    df["report_period_label"] = _period_label(report_month, report_year)
    df["source_file_name"] = source_path.name if source_path is not None else pd.NA
    df["source_file_path"] = str(source_path) if source_path is not None else pd.NA
    df["source_file_hash"] = _file_sha256(source_path)
    df["config_hash"] = _config_sha256(config)
    df["schema_version"] = schema_version

    refined_columns = [
        "page_num",
        "table_id",
        "capitolo",
        "sottocapitolo",
        "page_title",
        "page_subtitle",
        "page_subtitle_1",
        "period_agg",
        "period_desc",
        "period_start",
        "item_agg_2",
        "item_agg_1",
        "item_agg",
        "py_year",
        "act_year",
        "bdg_year",
        "py_value",
        "act_value",
        "bdg_value",
        "var_vs_py_abs",
        "var_vs_py_pct",
        "var_vs_bdg_abs",
        "var_vs_bdg_pct",
        "delta_abs",
        "delta_pct",
        "report_year",
        "report_month",
        "report_period_label",
        "source_file_name",
        "source_file_path",
        "source_file_hash",
        "config_hash",
        "run_id",
        "timestamp_utc",
        "schema_version",
    ]
    df_refined = df[refined_columns].copy()
    df_refined["record_hash"] = _build_record_hash(df_refined)

    ordered_columns = refined_columns + ["record_hash"]
    return df_refined[ordered_columns]
