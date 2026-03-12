from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
from loguru import logger

from ...common.utilities import norm


@dataclass
class TablePart:
    df: pd.DataFrame
    data_cols: List[int]
    part_id: int = 1
    parent_id: Optional[int] = None


def _positional_similarity(rowA, rowB):
    a = [norm(x) for x in rowA]
    b = [norm(x) for x in rowB]
    a = [x for x in a if x != ""]
    b = [x for x in b if x != ""]
    m = min(len(a), len(b))
    if m == 0:
        return 0.0
    return sum(1 for i in range(m) if a[i] == b[i]) / m


class TableSlicer:
    @staticmethod
    def split_side_by_side_half(
        df: pd.DataFrame,
        data_column: List[int],
        header_rows=(0, 1),
        sim_thresholds=(0.60, 0.95),
        keep_common_cols=True,
        debug=False,
        parent_id: Optional[int] = None,
        base_part_id: int = 1,
    ):
        """
        Ritorna: List[TablePart]
          - [TablePart(df,...)] se non splitta
          - [TablePart(df_left,...), TablePart(df_right,...)] se splitta
        """
        # guardrail
        if df is None or len(df) == 0 or not data_column:
            return [TablePart(df=df, data_cols=list(data_column), part_id=base_part_id, parent_id=parent_id)]
        if any(r >= len(df) for r in header_rows):
            return [TablePart(df=df, data_cols=list(data_column), part_id=base_part_id, parent_id=parent_id)]

        n_data = len(data_column)
        if n_data < 2:
            return [TablePart(df=df, data_cols=list(data_column), part_id=base_part_id, parent_id=parent_id)]

        mezzo = n_data // 2
        prima_meta = data_column[:mezzo]
        seconda_meta = data_column[mezzo:]

        sims = []
        for r in header_rows:
            rowA = df.loc[r, prima_meta].tolist()
            rowB = df.loc[r, seconda_meta].tolist()
            sim = _positional_similarity(rowA, rowB)
            sims.append(sim)

            if debug:
                logger.debug(f"[DEBUG] row {r} similarity={sim:.2f}")
                logger.debug(f"  A: {[norm(x) for x in rowA]}")
                logger.debug(f"  B: {[norm(x) for x in rowB]}")
                logger.debug("split_side_by_side_half: row={} similarity={:.2f}", r, sim)

        do_split = all(sim >= thr for sim, thr in zip(sims, sim_thresholds))
        if not do_split:
            return [TablePart(df=df, data_cols=list(data_column), part_id=base_part_id, parent_id=parent_id)]

        # colonne comuni (audit ecc.)
        if keep_common_cols:
            data_set = set(data_column)
            common_cols = [c for c in df.columns if c not in data_set]
        else:
            common_cols = []

        df_left = df[common_cols + prima_meta].copy()
        df_right = df[common_cols + seconda_meta].copy()

        # id figli:  base*10+1 e base*10+2 (semplice e tracciabile)
        left_id = base_part_id * 10 + 1
        right_id = base_part_id * 10 + 2

        return [
            TablePart(df=df_left, data_cols=list(prima_meta), part_id=left_id, parent_id=base_part_id),
            TablePart(df=df_right, data_cols=list(seconda_meta), part_id=right_id, parent_id=base_part_id),
        ]


def split_side_by_side_half(
    df: pd.DataFrame,
    data_column: List[int],
    header_rows=(0, 1),
    sim_thresholds=(0.60, 0.95),
    keep_common_cols=True,
    debug=False,
    parent_id: Optional[int] = None,
    base_part_id: int = 1,
):
    return TableSlicer.split_side_by_side_half(
        df=df,
        data_column=data_column,
        header_rows=header_rows,
        sim_thresholds=sim_thresholds,
        keep_common_cols=keep_common_cols,
        debug=debug,
        parent_id=parent_id,
        base_part_id=base_part_id,
    )
