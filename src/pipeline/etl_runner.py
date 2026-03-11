from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger

from pdfdataextractor import extract_table_pages
from pdfdataextractor.config import load_config, validate_page_config

from .HeaderProcessor import HeaderProcessor
from .TableSlicer import TableSlicer
from .TableSplitter import find_table_split_points, find_sections_by_keyword, split_by_points
from .TitleExtractor import estrai_titolo_pagina
from .utilities import recupera_livello_aggregazione
from .DataQuality import DataQuality
from .transforms import (
    clean_percentage_smart,
    fix_numeric_smart_scan,
    apply_capitoli,
    map_period_start,
    apply_period_desc,
    finalize_columns,
)


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def run_pipeline(config: dict, project_root: Path | None = None):
    project_root = project_root or Path(__file__).resolve().parents[2]
    config_path = _resolve_path(project_root, config["extraction_config_path"])
    extraction_cfg = load_config(config_path)

    pdf_path = _resolve_path(project_root, extraction_cfg["pdf_path"])
    page_config = validate_page_config(extraction_cfg["page_config"])
    threshold_righe = float(extraction_cfg.get("threshold_righe", 2))

    result = extract_table_pages(
        pdf_path,
        page_config=page_config,
        threshold_righe=threshold_righe,
        return_phrases=True,
        return_stats=True,
        return_log=True,
        return_lineage=True,
        return_cells=True,
    )

    tables = result["tables"]

    hp = HeaderProcessor(
        header_tokens=set(config["header_tokens"]),
        rules=config.get("header_rules", []),
        debug=config.get("debug", False),
    )

    dfs_refined = []
    errors_list = []

    for k, v in page_config.items():
        n_column = v
        n_page = k
        data_column = [col for col in range(0, n_column)]

        df_raw = tables[n_page]
        df_refined = df_raw.copy()

        try:
            titolo_pagina = estrai_titolo_pagina(
                df=df_refined,
                data_column=data_column,
                max_title_rows=config["title"]["max_title_rows"],
                drop_row=config["title"]["drop_row"],
                debug=config["title"]["debug"],
            )
            df_refined["page_title"] = titolo_pagina

            sotto_titolo_pagina = estrai_titolo_pagina(
                df=df_refined,
                data_column=data_column,
                max_title_rows=config["title"]["max_title_rows"],
                drop_row=config["title"]["drop_row"],
                debug=config["title"]["debug"],
            )
            df_refined["page_subtitle"] = sotto_titolo_pagina

            split_points = find_table_split_points(
                df_refined,
                data_column,
                HEADER_TOKENS=set(config["header_tokens"]),
                empty_threshold=config["split"]["empty_threshold"],
                confirm_header=config["split"]["confirm_header"],
                debug=config["split"]["debug"],
            )

            if not split_points:
                split_points = find_sections_by_keyword(
                    df_refined,
                    data_column,
                    HEADER_TOKENS=set(config["header_tokens"]),
                    keywords=config["split"]["keywords_primary"],
                    debug=config["split"]["debug"],
                )

            if not split_points:
                split_points = find_sections_by_keyword(
                    df_refined,
                    data_column,
                    HEADER_TOKENS=set(config["header_tokens"]),
                    keywords=config["split"]["keywords_fallback"],
                    debug=config["split"]["debug"],
                )

            dfs = split_by_points(df_refined, split_points)

            if dfs:
                for table_idx, table in enumerate(dfs):
                    sottotitolo_pagina1 = estrai_titolo_pagina(
                        df=table,
                        data_column=data_column,
                        max_title_rows=config["title"]["max_title_rows"],
                        drop_row=config["title"]["drop_row"],
                        debug=config["title"]["debug"],
                    )
                    table["page_subtitle_1"] = sottotitolo_pagina1

                    parts = TableSlicer.split_side_by_side_half(
                        df=table,
                        data_column=data_column,
                        header_rows=tuple(config["slicer"]["header_rows"]),
                        sim_thresholds=tuple(config["slicer"]["sim_thresholds"]),
                        debug=config["slicer"]["debug"],
                    )

                    for sub_idx, sub_table in enumerate(parts):
                        sub_table.df = sub_table.df.reset_index(drop=True)

                        period_ref, nomi_colonne = hp.estrai_nomi_colonne(
                            df=sub_table.df,
                            col_indices=sub_table.data_cols,
                            row1_idx=0,
                            row2_idx=1,
                            drop_row=True,
                            debug=config.get("debug", False),
                            page_ref=n_page,
                            period_placeholder=config.get("period_placeholder"),
                            period_tokens=tuple(config.get("period_tokens", [])),
                            period_min_hits=config.get("period_min_hits", 2),
                        )

                        sub_table.df["period_agg"] = period_ref
                        sub_table.df["period_start"] = np.nan
                        sub_table.df = hp.rinomina_colonne(
                            sub_table.df,
                            sub_table.data_cols,
                            nomi_colonne,
                            page_ref=n_page,
                        )

                        sub_table.df["table_id"] = table_idx

                        sub_table.df = recupera_livello_aggregazione(
                            sub_table.df,
                            config["aggregation_keywords"],
                            "item_agg",
                            "item_agg_1",
                        )

                        static_cols = config["static_column_list"]
                        audit_cols = config["audit_column_list"]
                        dfs_refined.append(
                            sub_table.df[audit_cols + static_cols + list(nomi_colonne)]
                        )
        except Exception as exc:
            logger.error(f"Errore:  Pagina N: [{k}] Colonne N: [{v}]{exc}")
            errors_list.append({"page": k, "n_col": v, "e_des": exc})
            continue

    dq = DataQuality(preview_limit=config["dataquality"]["preview_limit"])
    res = dq.run(dfs_refined, mutate=config["dataquality"]["mutate"])

    qc_summary = res.qc_summary
    errors_list.append(res.errors_list)
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

    df_final = finalize_columns(df_final, config["final_columns"])
    df_final["timestamp_utc"] = df_final["timestamp_utc"].dt.tz_localize(None)

    return {
        "df_final": df_final,
        "qc_summary": qc_summary,
        "errors_list": errors_list,
        "df_to_analyze": df_to_analyze,
        "log_percentage": log_percentage,
    }
