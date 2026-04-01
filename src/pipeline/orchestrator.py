from pathlib import Path

import pandas as pd

from .stages.extraction import extract_raw
from .stages.reconstruction import reconstruct_tables
from .stages.canonicalization import canonicalize
from .stages.publish import publish_outputs


def run_pipeline(
    config: dict,
    project_root: Path | None = None,
    output_paths: dict | None = None,
    publish: bool = True,
):
    pd.set_option("future.no_silent_downcasting", True)
    project_root = project_root or Path(__file__).resolve().parents[2]

    extraction_out = extract_raw(config, project_root=project_root)
    reconstruction_out = reconstruct_tables(
        extraction_out.tables, extraction_out.page_config, config
    )
    canonical_out = canonicalize(
        reconstruction_out.dfs_refined, reconstruction_out.errors_list, config
    )

    result = {
        "df_final": canonical_out.df_final,
        "qc_summary": canonical_out.qc_summary,
        "errors_list": canonical_out.errors_list,
        "df_to_analyze": canonical_out.df_to_analyze,
        "log_percentage": canonical_out.log_percentage,
    }

    if publish and output_paths:
        publish_outputs(result, output_paths)

    return result
