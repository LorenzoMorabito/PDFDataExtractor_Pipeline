import numpy as np
import re
from collections import Counter
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class DataQualityResult:
    qc_summary: List[Dict[str, Any]]
    errors_list: List[Dict[str, Any]]
    df_to_analyze: List[Any]           # list[pd.DataFrame], ma lasciamo Any
    clean_dfs: List[Any]               # list[pd.DataFrame]
    problem_idxs: List[int]

class DataQuality:
    """
    Data quality checks per garantire unionabilità e rilevare header rotti.

    Check:
      - nomi colonna duplicati
      - nomi colonna che sembrano numeri/percentuali/anni
      - nomi colonna con caratteri "sporchi" o token sospetti
    """

    def __init__(
        self,
        bad_tokens: Optional[List[str]] = None,
        preview_limit: int = 8,
        allow_chars_pattern: str = r'^[A-Za-z0-9_]+$',  # se vuoi essere più permissivo, cambia qui
        debug: bool = False,
    ):
        self.preview_limit = preview_limit
        self.debug = debug

        # tokens sospetti (personalizzabili)
        if bad_tokens is None:
            bad_tokens = ["december", "ytd", "eur_pct_vs_bdg", "eur_act", "eur_ytd", "eur_december"]
        self.bad_tokens = bad_tokens

        # regex numeriche (stile EU)
        self.RE_YEAR = re.compile(r'^\d{4}$')
        self.RE_INTLIKE = re.compile(r'^[+-]?\d{1,3}(\.\d{3})*$')      # 1.426.832
        self.RE_FLOATLIKE = re.compile(r'^[+-]?\d+(?:[.,]\d+)?$')      # 12,7 oppure 12.7 oppure 12
        self.RE_PCTLK = re.compile(r'^[+-]?\d+(?:[.,]\d+)?%$')         # 12,7%

        # caratteri “sporchi”: tutto ciò che non è alfanumerico/_ (nota: underscore è incluso in \w)
        self.RE_BAD_CHARS = re.compile(r'[^\w\s]', re.I)

        # tokens sospetti: costruita da lista
        tok = "|".join(re.escape(t) for t in self.bad_tokens)
        self.RE_BAD_TOKENS = re.compile(rf'\b({tok})\b', re.I)

        # allowlist (opzionale): se vuoi controllare rigidamente il formato
        self.RE_ALLOW = re.compile(allow_chars_pattern)

    @staticmethod
    def _find_duplicate_cols(cols: List[str]) -> List[str]:
        cnt = Counter(cols)
        return [c for c, n in cnt.items() if n > 1]

    def _looks_numeric_colname(self, c: str) -> bool:
        c = str(c).strip()
        return bool(
            self.RE_YEAR.match(c)
            or self.RE_PCTLK.match(c)
            or self.RE_INTLIKE.match(c)
            or self.RE_FLOATLIKE.match(c)
        )

    def _find_bad_cols(self, cols: List[str]) -> Tuple[List[str], List[str]]:
        bad_chars = []
        bad_tokens = []
        for c in cols:
            s = str(c)
            if self.RE_BAD_CHARS.search(s):
                bad_chars.append(s)
            if self.RE_BAD_TOKENS.search(s):
                bad_tokens.append(s)
        return bad_chars, bad_tokens

    @staticmethod
    def _get_page_num(df) -> float:
        try:
            if "page_num" in df.columns:
                v = df["page_num"].dropna().unique()
                if len(v) > 0:
                    return int(v[0])
        except Exception:
            pass
        return np.nan

    def run(self, dfs_refined: List[Any], mutate: bool = False) -> DataQualityResult:
        """
        mutate=False => non modifica la lista originale, ritorna clean_dfs separata.
        mutate=True  => poppa dalla lista originale (come fai ora).
        """
        qc_summary: List[Dict[str, Any]] = []
        errors_list: List[Dict[str, Any]] = []
        problem_idxs: List[int] = []

        for i, df in enumerate(dfs_refined):
            cols = [str(c) for c in df.columns]
            n_col = len(cols)
            pg_n = self._get_page_num(df)

            dup_cols = self._find_duplicate_cols(cols)
            numeric_like = [c for c in cols if self._looks_numeric_colname(c)]
            bad_chars, bad_tokens = self._find_bad_cols(cols)

            issues = []
            if dup_cols: issues.append("DUPLICATE_COLS")
            if numeric_like: issues.append("NUMERIC_COLNAMES")
            if bad_chars: issues.append("BAD_CHARS")
            if bad_tokens: issues.append("BAD_TOKENS")

            is_problem = len(issues) > 0
            if is_problem:
                problem_idxs.append(i)

            # summary 1 record per df
            qc_summary.append({
                "idx": i,
                "page": pg_n,
                "n_col": n_col,
                "is_problem": is_problem,
                "issues": "|".join(issues) if issues else "",
                "dup_n": len(dup_cols),
                "numeric_n": len(numeric_like),
                "bad_chars_n": len(bad_chars),
                "bad_tokens_n": len(bad_tokens),
                "dup_cols": dup_cols[:self.preview_limit],
                "numeric_cols": numeric_like[:self.preview_limit],
                "bad_chars_cols": bad_chars[:self.preview_limit],
                "bad_token_cols": bad_tokens[:self.preview_limit],
            })

            # event log (più righe)
            if dup_cols:
                errors_list.append({"page": pg_n, "n_col": n_col, "e_des": f"DUPLICATE_COLS: {dup_cols}"})
            if numeric_like:
                errors_list.append({"page": pg_n, "n_col": n_col, "e_des": f"NUMERIC_COLNAMES: {numeric_like}"})
            if bad_chars:
                errors_list.append({"page": pg_n, "n_col": n_col, "e_des": f"BAD_CHARS_IN_COLNAMES: {bad_chars}"})
            if bad_tokens:
                errors_list.append({"page": pg_n, "n_col": n_col, "e_des": f"BAD_TOKENS_IN_COLNAMES: {bad_tokens}"})

        # estrai DF problematici
        df_to_analyze = []
        if mutate:
            for idx in sorted(set(problem_idxs), reverse=True):
                df_to_analyze.append(dfs_refined.pop(idx))
            clean_dfs = dfs_refined
        else:
            problem_set = set(problem_idxs)
            clean_dfs = [df for j, df in enumerate(dfs_refined) if j not in problem_set]
            df_to_analyze = [df for j, df in enumerate(dfs_refined) if j in problem_set]

        return DataQualityResult(
            qc_summary=qc_summary,
            errors_list=errors_list,
            df_to_analyze=df_to_analyze,
            clean_dfs=clean_dfs,
            problem_idxs=sorted(set(problem_idxs))
        )