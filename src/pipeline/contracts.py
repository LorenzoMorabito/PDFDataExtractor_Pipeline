from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd


@dataclass
class ExtractionOutput:
    tables: Dict[Any, pd.DataFrame]
    page_config: Dict[str, int]
    extraction_cfg: Dict[str, Any]
    raw_result: Dict[str, Any]


@dataclass
class ReconstructionOutput:
    dfs_refined: List[pd.DataFrame]
    errors_list: List[Dict[str, Any]]


@dataclass
class CanonicalizationOutput:
    df_refined: pd.DataFrame
    df_final: pd.DataFrame
    qc_summary: List[Dict[str, Any]]
    errors_list: List[Dict[str, Any]]
    df_to_analyze: List[pd.DataFrame]
    log_percentage: List[Dict[str, Any]]
