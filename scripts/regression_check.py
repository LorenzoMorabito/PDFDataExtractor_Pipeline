import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline.orchestrator import run_pipeline


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df[col] = df[col].apply(lambda x: json.dumps(x, sort_keys=True) if isinstance(x, (list, dict)) else x)
    return df


def _fingerprint(df: pd.DataFrame, ignore_cols: set[str]) -> dict:
    df = df.copy()
    for c in ignore_cols:
        if c in df.columns:
            df = df.drop(columns=[c])
    df = _normalize_df(df)
    df = df.sort_index(axis=1)
    row_hash = pd.util.hash_pandas_object(df, index=True).sum()
    return {
        "shape": list(df.shape),
        "columns": list(df.columns),
        "hash": int(row_hash),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--baseline", default="artifacts/baseline.json")
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--ignore-cols", default="timestamp_utc,run_id")
    args = parser.parse_args()

    ignore_cols = {c.strip() for c in args.ignore_cols.split(",") if c.strip()}
    config_path = (ROOT / args.config).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))

    result = run_pipeline(config, project_root=ROOT, publish=False)
    fp = _fingerprint(result["df_final"], ignore_cols)
    qc_df = pd.DataFrame(result["qc_summary"])
    err_df = pd.DataFrame(result["errors_list"])
    fp_qc = _fingerprint(qc_df, set())
    fp_err = _fingerprint(err_df, set())
    fp["qc_summary"] = fp_qc
    fp["errors_list"] = fp_err

    baseline_path = (ROOT / args.baseline).resolve()
    baseline_path.parent.mkdir(parents=True, exist_ok=True)

    if args.write_baseline or not baseline_path.exists():
        baseline_path.write_text(json.dumps(fp, indent=2), encoding="utf-8")
        print(f"Baseline written: {baseline_path}")
        return 0

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    if fp != baseline:
        print("REGRESSION CHECK FAILED")
        print("Current:", fp)
        print("Baseline:", baseline)
        return 1

    print("REGRESSION CHECK PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
