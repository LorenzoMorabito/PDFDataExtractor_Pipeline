
import pandas as pd
import numpy as np
from pathlib import Path

INPUT = Path("/mnt/data/df_canonical_FEB_2026.csv")
OUTDIR = Path("/mnt/data/report_model_output")
OUTDIR.mkdir(parents=True, exist_ok=True)

TEXT_COLS = [
    "page_title","page_subtitle","page_subtitle_detail","chapter_name","subchapter_name",
    "entity_name","entity_group_1","entity_group_2","metric_name","metric_unit",
    "scenario","comparison_target","source_measure_column","report_period_label",
    "report_month_name","source_file_name"
]

MEASURE_MAP = {
    "2025_act": "py_actual_value",
    "2026_act": "actual_value",
    "2026_bdg": "budget_value",
    "eur_vs_act": "variance_vs_py_abs",
    "pct_vs_act": "variance_vs_py_pct",
    "eur_vs_bdg": "variance_vs_budget_abs",
    "pct_vs_bdg": "variance_vs_budget_pct",
    "eur_delta": "delta_abs",
    "pct_delta": "delta_pct",
}

KEY_COLS = [
    "report_year","report_month","report_month_name","report_period_label",
    "page_num","page_title","page_subtitle","page_subtitle_detail",
    "chapter_name","subchapter_name","period_scope","period_start_date",
    "section_family","cluster","entity_label","entity_parent_1","entity_parent_2"
]

def clean_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    for c in TEXT_COLS:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()
            df[c] = df[c].replace({
                "<NA>": pd.NA,
                "nan": pd.NA,
                "NaN": pd.NA,
                "": pd.NA,
                "\\": pd.NA,
            })
    return df

def _safe_upper(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).upper()

def classify_section(page_title: str, page_subtitle: str) -> str:
    pt = _safe_upper(page_title)
    ps = _safe_upper(page_subtitle)

    if "MENARINI GROUP" in pt:
        return "GROUP_OVERVIEW"
    if pt == "PHARMA AREAS" and ps == "BY BUSINESS":
        return "BU"
    if pt == "PHARMA AREAS" and ps == "BY REGION":
        return "REGION"
    if pt == "PHARMA COUNTRIES":
        return "COUNTRY_DEVIATION"
    if pt == "PHARMA PRODUCTS":
        return "PRODUCT_DEVIATION"
    if ("BY PRODUCT" in ps) or pt.startswith("APAC - ") or pt in {
        "WESTERN EUROPE", "CENTRAL & EASTERN EUROPE", "TURKEY",
        "AFRICA & MIDDLE EAST", "LATAM & CENTRAL AMERICA", "LATAM"
    }:
        return "AREA_PRODUCT"
    if ps == "BY COUNTRY":
        return "COUNTRY_DETAIL"
    if ps == "BY ENTITY":
        return "ENTITY_DETAIL"
    return "OTHER"

def classify_cluster(page_title: str) -> str:
    pt = _safe_upper(page_title)

    if pt in {"WESTERN EUROPE", "ITALY"}:
        return "WE"
    if pt in {"CENTRAL & EASTERN EUROPE", "TURKEY"}:
        return "BC_TURKEY"
    if pt == "ASIA PACIFIC" or pt.startswith("APAC - "):
        return "APAC"
    if pt in {"LATAM & CENTRAL AMERICA", "CENTRAL AMERICA", "LATAM"}:
        return "LATAM"
    if pt == "AFRICA & MIDDLE EAST":
        return "MEA"
    if pt in {
        "MENARINI GROUP OVERVIEW",
        "MENARINI GROUP PERFORMANCES OVERVIEW",
        "PHARMA AREAS",
        "PHARMA COUNTRIES",
        "PHARMA PRODUCTS",
    }:
        return "TOTAL"
    return "OTHER"

def build_atomic_canonical(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["entity_label"] = df["entity_name"].fillna(df["entity_group_2"]).fillna(df["entity_group_1"])
    df["entity_parent_1"] = df["entity_group_1"]
    df["entity_parent_2"] = df["entity_group_2"]

    df["section_family"] = [
        classify_section(pt, ps) for pt, ps in zip(df["page_title"], df["page_subtitle"])
    ]
    df["cluster"] = [classify_cluster(pt) for pt in df["page_title"]]
    df["measure_key"] = df["source_measure_column"].map(MEASURE_MAP).fillna(df["source_measure_column"])
    return df

def build_collision_audit(df_atomic: pd.DataFrame) -> pd.DataFrame:
    tmp = df_atomic.copy()
    for c in KEY_COLS:
        tmp[c] = tmp[c].fillna("__NA__")

    audit = (
        tmp.groupby(KEY_COLS + ["measure_key"], as_index=False)["metric_value"]
        .agg(rows="size", distinct_values="nunique", metric_values=lambda s: list(pd.unique(s.dropna()))[:10])
    )
    audit = audit[audit["rows"] > 1].copy()

    for c in KEY_COLS:
        audit[c] = audit[c].replace("__NA__", pd.NA)
    return audit

def build_business_fact(df_atomic: pd.DataFrame) -> pd.DataFrame:
    tmp = df_atomic.copy()
    for c in KEY_COLS:
        tmp[c] = tmp[c].fillna("__NA__")

    agg = (
        tmp.groupby(KEY_COLS + ["measure_key"], as_index=False)["metric_value"]
        .sum()
    )

    fact = (
        agg.pivot(index=KEY_COLS, columns="measure_key", values="metric_value")
        .reset_index()
    )
    fact.columns.name = None
    fact = fact.replace("__NA__", pd.NA)

    fact["entity_type"] = fact["section_family"].map({
        "BU": "BUSINESS_UNIT",
        "REGION": "REGION",
        "COUNTRY_DEVIATION": "COUNTRY",
        "COUNTRY_DETAIL": "COUNTRY",
        "PRODUCT_DEVIATION": "PRODUCT",
        "AREA_PRODUCT": "PRODUCT",
        "ENTITY_DETAIL": "ENTITY",
        "GROUP_OVERVIEW": "GROUP_LINE",
    }).fillna("UNKNOWN")

    fact["observation_id"] = (
        fact["report_period_label"].astype(str) + "|" +
        fact["period_scope"].astype(str) + "|" +
        fact["section_family"].astype(str) + "|" +
        fact["page_title"].astype(str) + "|" +
        fact["page_subtitle"].astype(str) + "|" +
        fact["entity_label"].astype(str)
    )

    detail_upper = fact["page_subtitle_detail"].fillna("").str.upper()
    mask_bdg = detail_upper.eq("VS BUDGET 2026")
    mask_py = detail_upper.eq("VS ACTUAL 2025")

    if "delta_abs" in fact.columns:
        fact.loc[mask_bdg & fact["variance_vs_budget_abs"].isna(), "variance_vs_budget_abs"] = fact.loc[mask_bdg & fact["variance_vs_budget_abs"].isna(), "delta_abs"]
        fact.loc[mask_py & fact["variance_vs_py_abs"].isna(), "variance_vs_py_abs"] = fact.loc[mask_py & fact["variance_vs_py_abs"].isna(), "delta_abs"]
    if "delta_pct" in fact.columns:
        fact.loc[mask_bdg & fact["variance_vs_budget_pct"].isna(), "variance_vs_budget_pct"] = fact.loc[mask_bdg & fact["variance_vs_budget_pct"].isna(), "delta_pct"]
        fact.loc[mask_py & fact["variance_vs_py_pct"].isna(), "variance_vs_py_pct"] = fact.loc[mask_py & fact["variance_vs_py_pct"].isna(), "delta_pct"]

    return fact

def build_semantic_long(fact: pd.DataFrame) -> pd.DataFrame:
    common_cols = [
        "observation_id","report_year","report_month","report_month_name","report_period_label",
        "page_num","page_title","page_subtitle","page_subtitle_detail",
        "chapter_name","subchapter_name","period_scope","period_start_date",
        "section_family","cluster","entity_type","entity_label","entity_parent_1",
        "entity_parent_2","actual_value"
    ]

    rows = []
    for _, r in fact.iterrows():
        common = {c: r.get(c) for c in common_cols}

        detail = _safe_upper(r.get("page_subtitle_detail"))

        has_py = (
            pd.notna(r.get("py_actual_value")) or
            pd.notna(r.get("variance_vs_py_abs")) or
            pd.notna(r.get("variance_vs_py_pct")) or
            detail == "VS ACTUAL 2025"
        )
        has_bdg = (
            pd.notna(r.get("budget_value")) or
            pd.notna(r.get("variance_vs_budget_abs")) or
            pd.notna(r.get("variance_vs_budget_pct")) or
            detail == "VS BUDGET 2026"
        )

        if has_py:
            rows.append({
                **common,
                "comparison_type": "PY",
                "base_value": r.get("py_actual_value"),
                "variance_abs": r.get("variance_vs_py_abs"),
                "variance_pct": r.get("variance_vs_py_pct"),
            })

        if has_bdg:
            rows.append({
                **common,
                "comparison_type": "BDG",
                "base_value": r.get("budget_value"),
                "variance_abs": r.get("variance_vs_budget_abs"),
                "variance_pct": r.get("variance_vs_budget_pct"),
            })

    out = pd.DataFrame(rows)
    out["rank_sign"] = np.where(
        out["variance_abs"] > 0, "POSITIVE",
        np.where(out["variance_abs"] < 0, "NEGATIVE", "ZERO")
    )
    return out

def build_gold_tables(fact: pd.DataFrame, semantic_long: pd.DataFrame):
    gold_overview = fact[fact["section_family"].isin(["GROUP_OVERVIEW", "BU", "REGION"])].copy()
    gold_overview = gold_overview[[
        "observation_id","report_period_label","period_scope","section_family",
        "page_title","page_subtitle","cluster","entity_label","entity_type",
        "actual_value","budget_value","py_actual_value",
        "variance_vs_budget_abs","variance_vs_budget_pct",
        "variance_vs_py_abs","variance_vs_py_pct"
    ]]

    gold_moves = semantic_long[semantic_long["section_family"].isin(["COUNTRY_DEVIATION", "PRODUCT_DEVIATION"])].copy()
    gold_moves["pos_rank"] = gold_moves.groupby(
        ["report_period_label","section_family","comparison_type"]
    )["variance_abs"].rank(ascending=False, method="dense")
    gold_moves["neg_rank"] = gold_moves.groupby(
        ["report_period_label","section_family","comparison_type"]
    )["variance_abs"].rank(ascending=True, method="dense")
    gold_moves = gold_moves[[
        "observation_id","report_period_label","period_scope","section_family",
        "comparison_type","entity_label","entity_type",
        "actual_value","base_value","variance_abs","variance_pct",
        "rank_sign","pos_rank","neg_rank"
    ]]

    gold_area = semantic_long[semantic_long["section_family"].eq("AREA_PRODUCT")].copy()
    gold_area["pos_rank"] = gold_area.groupby(
        ["report_period_label","cluster","comparison_type"]
    )["variance_abs"].rank(ascending=False, method="dense")
    gold_area["neg_rank"] = gold_area.groupby(
        ["report_period_label","cluster","comparison_type"]
    )["variance_abs"].rank(ascending=True, method="dense")
    gold_area = gold_area[[
        "observation_id","report_period_label","period_scope","cluster",
        "page_title","page_subtitle","page_subtitle_detail",
        "comparison_type","entity_label",
        "actual_value","base_value","variance_abs","variance_pct",
        "rank_sign","pos_rank","neg_rank"
    ]]

    return gold_overview, gold_moves, gold_area

def main():
    raw = pd.read_csv(INPUT)
    raw = clean_text_columns(raw)

    atomic = build_atomic_canonical(raw)
    collision_audit = build_collision_audit(atomic)
    business_fact = build_business_fact(atomic)
    semantic_long = build_semantic_long(business_fact)
    gold_overview, gold_moves, gold_area = build_gold_tables(business_fact, semantic_long)

    atomic.to_csv(OUTDIR / "silver_atomic_canonical.csv", index=False)
    collision_audit.to_csv(OUTDIR / "silver_collision_audit.csv", index=False)
    business_fact.to_csv(OUTDIR / "silver_business_fact.csv", index=False)
    semantic_long.to_csv(OUTDIR / "silver_semantic_long.csv", index=False)
    gold_overview.to_csv(OUTDIR / "gold_overview.csv", index=False)
    gold_moves.to_csv(OUTDIR / "gold_country_product_moves.csv", index=False)
    gold_area.to_csv(OUTDIR / "gold_area_products.csv", index=False)

    print("Created:")
    for p in sorted(OUTDIR.glob("*.csv")):
        print(" -", p.name)

if __name__ == "__main__":
    main()
