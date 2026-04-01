import numpy as np
import pandas as pd

from ...contracts import CanonicalizationOutput
from ...domains.canonicalization.DataQuality import DataQuality
from ...transforms import (
    apply_capitoli,
    apply_period_desc,
    build_refined_dataframe,
    clean_percentage_smart,
    finalize_columns,
    fix_numeric_smart_scan,
    map_period_start,
)


def canonicalize(
    dfs_refined: list,
    errors_list: list,
    config: dict,
    *,
    extraction_cfg: dict | None = None,
    project_root=None,
) -> CanonicalizationOutput:
    dq = DataQuality(preview_limit=config["dataquality"]["preview_limit"])
    res = dq.run(dfs_refined, mutate=config["dataquality"]["mutate"])

    qc_summary = res.qc_summary
    errors_list = list(errors_list) + list(res.errors_list)
    df_to_analyze = res.df_to_analyze
    dfs_refined_clean = res.clean_dfs

    df_final = pd.concat(dfs_refined_clean, ignore_index=True)

    df_final = map_period_start(df_final, config["year_ref"])
    df_final = df_final.replace([" ", "", "n.s.", "null", "n.s"], np.nan)
    df_final["timestamp_utc"] = pd.to_datetime(df_final["timestamp_utc"], utc=True)

    df_final, log_percentage = clean_percentage_smart(
        df_final,
        threshold=config["cleaning"]["percent_threshold"],
        max_loss_ratio=config["cleaning"]["percent_max_loss_ratio"],
    )
    df_final = fix_numeric_smart_scan(
        df_final,
        pre_scan_threshold=config["cleaning"]["numeric_pre_scan_threshold"],
        max_loss_ratio=config["cleaning"]["numeric_max_loss_ratio"],
    )

    df_final = apply_capitoli(df_final, config["capitoli"])
    df_final = apply_period_desc(df_final)
    df_refined = build_refined_dataframe(
        df_final,
        year_ref=config["year_ref"],
        config=config,
        source_file_path=(extraction_cfg or {}).get("pdf_path"),
        project_root=project_root,
    )

    df_final = finalize_columns(df_final, config["final_columns"])
    df_final["timestamp_utc"] = df_final["timestamp_utc"].dt.tz_localize(None)
    df_refined["timestamp_utc"] = pd.to_datetime(df_refined["timestamp_utc"], utc=True).dt.tz_localize(None)

    return CanonicalizationOutput(
        df_refined=df_refined,
        df_final=df_final,
        qc_summary=qc_summary,
        errors_list=errors_list,
        df_to_analyze=df_to_analyze,
        log_percentage=log_percentage,
    )
