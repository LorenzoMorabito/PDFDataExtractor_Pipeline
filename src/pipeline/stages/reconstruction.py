import numpy as np
from loguru import logger

from ..domains.reconstruction.HeaderProcessor import HeaderProcessor
from ..domains.reconstruction.TableSlicer import TableSlicer
from ..domains.reconstruction.TableSplitter import find_table_split_points, find_sections_by_keyword, split_by_points
from ..domains.reconstruction.TitleExtractor import estrai_titolo_pagina
from ..common.utilities import recupera_livello_aggregazione
from ..contracts import ReconstructionOutput


def reconstruct_tables(tables: dict, page_config: dict, config: dict) -> ReconstructionOutput:
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

    return ReconstructionOutput(dfs_refined=dfs_refined, errors_list=errors_list)
