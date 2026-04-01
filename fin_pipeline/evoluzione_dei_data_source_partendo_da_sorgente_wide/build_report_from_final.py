import pandas as pd
import numpy as np
from pathlib import Path

INPUT = Path("/mnt/data/df_final_FEB_2026.xlsx")
OUTDIR = Path("/mnt/data/report_model_output_from_final")
OUTDIR.mkdir(exist_ok=True)

def _safe_upper(value):
    if pd.isna(value):
        return ""
    return str(value).upper().strip()

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

def derive_entity(row):
    a2, a1, a = row["item_agg_2"], row["item_agg_1"], row["item_agg"]
    if pd.notna(a):
        return a, a1, a2
    if pd.notna(a1):
        return a1, a2, pd.NA
    return a2, pd.NA, pd.NA

df = pd.read_excel(INPUT)

text_cols = ["capitolo","sottocapitolo","page_title","page_subtitle","page_subtitle_1","period_desc","item_agg_2","item_agg_1","item_agg","run_id"]
for c in text_cols:
    df[c] = df[c].astype("string").str.strip()
    df[c] = df[c].replace({"<NA>": pd.NA, "nan": pd.NA, "NaN": pd.NA, "": pd.NA})

df["period_start"] = pd.to_datetime(df["period_start"], errors="coerce")
df["timestamp_utc"] = pd.to_datetime(df["timestamp_utc"], errors="coerce")
df["report_year"] = df["period_start"].dt.year.fillna(df["timestamp_utc"].dt.year).astype("Int64")
df["report_month"] = df["period_start"].dt.month.fillna(df["timestamp_utc"].dt.month).astype("Int64")
df["report_month_name"] = df["period_start"].dt.strftime("%B").str.upper()
df["report_period_label"] = df["period_start"].dt.strftime("%b_%Y").str.upper()

metric_cols = ["2025_act","2026_act","2026_bdg","eur_vs_act","pct_vs_act","eur_vs_bdg","pct_vs_bdg","eur_delta","pct_delta"]

df = df.drop_duplicates().copy()
mask_empty = df[metric_cols].isna().all(axis=1) & df[["item_agg","item_agg_1","item_agg_2"]].isna().all(axis=1)
df = df.loc[~mask_empty].copy()
header_mask = df["item_agg"].astype("string").str.upper().isin(["EURO/000","COUNTRIES","TOTAL MANUF."])
df = df.loc[~header_mask.fillna(False)].copy()

entities = df.apply(derive_entity, axis=1, result_type="expand")
entities.columns = ["entity_label","entity_parent_1","entity_parent_2"]
df = pd.concat([df, entities], axis=1)

df["chapter_name"] = df["capitolo"]
df["subchapter_name"] = df["sottocapitolo"]
df["page_subtitle_detail"] = df["page_subtitle_1"]
df["period_scope"] = df["period_desc"].fillna("UNKNOWN")
df["period_start_date"] = df["period_start"].dt.strftime("%Y-%m-%d")
df["section_family"] = [classify_section(pt, ps) for pt, ps in zip(df["page_title"], df["page_subtitle"])]
df["cluster"] = [classify_cluster(pt) for pt in df["page_title"]]
df["ingested_at_utc"] = df["timestamp_utc"].dt.strftime("%Y-%m-%d %H:%M:%S")

entity_type_map = {
    "BU": "BUSINESS_UNIT",
    "REGION": "REGION",
    "COUNTRY_DEVIATION": "COUNTRY",
    "COUNTRY_DETAIL": "COUNTRY",
    "PRODUCT_DEVIATION": "PRODUCT",
    "AREA_PRODUCT": "PRODUCT",
    "ENTITY_DETAIL": "ENTITY",
    "GROUP_OVERVIEW": "GROUP_LINE",
}
df["entity_type"] = df["section_family"].map(entity_type_map).fillna("UNKNOWN")

df["observation_id"] = (
    df["report_period_label"].astype("string").fillna("NA") + "|" +
    df["period_scope"].astype("string").fillna("NA") + "|" +
    df["section_family"].astype("string").fillna("NA") + "|" +
    df["page_title"].astype("string").fillna("NA") + "|" +
    df["page_subtitle"].astype("string").fillna("NA") + "|" +
    df["entity_label"].astype("string").fillna("NA")
)

measure_map = {
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

id_cols = ["run_id","ingested_at_utc","report_year","report_month","report_month_name","report_period_label",
           "page_num","page_title","page_subtitle","page_subtitle_detail","chapter_name","subchapter_name",
           "period_scope","period_start_date","section_family","cluster","entity_type","entity_label",
           "entity_parent_1","entity_parent_2","observation_id"]

atomic = df[id_cols + metric_cols].melt(id_vars=id_cols, value_vars=metric_cols,
                                        var_name="source_measure_column", value_name="metric_value")
atomic = atomic[atomic["metric_value"].notna()].copy()
atomic["measure_key"] = atomic["source_measure_column"].map(measure_map).fillna(atomic["source_measure_column"])

fact = df[["report_year","report_month","report_month_name","report_period_label","page_num","page_title",
           "page_subtitle","page_subtitle_detail","chapter_name","subchapter_name","period_scope","period_start_date",
           "section_family","cluster","entity_label","entity_parent_1","entity_parent_2","2026_act","2026_bdg",
           "eur_delta","pct_delta","2025_act","eur_vs_bdg","pct_vs_bdg","eur_vs_act","pct_vs_act","entity_type",
           "observation_id"]].copy().rename(columns={
    "2026_act":"actual_value",
    "2026_bdg":"budget_value",
    "eur_delta":"delta_abs",
    "pct_delta":"delta_pct",
    "2025_act":"py_actual_value",
    "eur_vs_bdg":"variance_vs_budget_abs",
    "pct_vs_bdg":"variance_vs_budget_pct",
    "eur_vs_act":"variance_vs_py_abs",
    "pct_vs_act":"variance_vs_py_pct",
})

common_cols = ["observation_id","report_year","report_month","report_month_name","report_period_label",
               "page_num","page_title","page_subtitle","page_subtitle_detail","chapter_name","subchapter_name",
               "period_scope","period_start_date","section_family","cluster","entity_type","entity_label",
               "entity_parent_1","entity_parent_2","actual_value"]

rows = []
for _, r in fact.iterrows():
    common = {c: r.get(c) for c in common_cols}
    has_py = pd.notna(r.get("py_actual_value")) or pd.notna(r.get("variance_vs_py_abs")) or pd.notna(r.get("variance_vs_py_pct"))
    has_bdg = pd.notna(r.get("budget_value")) or pd.notna(r.get("variance_vs_budget_abs")) or pd.notna(r.get("variance_vs_budget_pct"))
    if has_py:
        rows.append({**common,"comparison_type":"PY","base_value":r.get("py_actual_value"),
                     "variance_abs":r.get("variance_vs_py_abs"),"variance_pct":r.get("variance_vs_py_pct")})
    if has_bdg:
        rows.append({**common,"comparison_type":"BDG","base_value":r.get("budget_value"),
                     "variance_abs":r.get("variance_vs_budget_abs"),"variance_pct":r.get("variance_vs_budget_pct")})

semantic = pd.DataFrame(rows)
semantic["rank_sign"] = np.where(semantic["variance_abs"] > 0, "POSITIVE",
                                 np.where(semantic["variance_abs"] < 0, "NEGATIVE", "ZERO"))

gold_overview = fact[fact["section_family"].isin(["GROUP_OVERVIEW","BU","REGION"])][[
    "observation_id","report_period_label","period_scope","section_family","page_title","page_subtitle","cluster",
    "entity_label","entity_type","actual_value","budget_value","py_actual_value",
    "variance_vs_budget_abs","variance_vs_budget_pct","variance_vs_py_abs","variance_vs_py_pct"
]].copy()

gold_moves = semantic[semantic["section_family"].isin(["COUNTRY_DEVIATION","PRODUCT_DEVIATION"])].copy()
gold_moves["pos_rank"] = gold_moves.groupby(["report_period_label","section_family","comparison_type"])["variance_abs"].rank(ascending=False, method="dense")
gold_moves["neg_rank"] = gold_moves.groupby(["report_period_label","section_family","comparison_type"])["variance_abs"].rank(ascending=True, method="dense")
gold_moves = gold_moves[["observation_id","report_period_label","period_scope","section_family","comparison_type",
                         "entity_label","entity_type","actual_value","base_value","variance_abs","variance_pct",
                         "rank_sign","pos_rank","neg_rank"]]

gold_area = semantic[semantic["section_family"].eq("AREA_PRODUCT")].copy()
gold_area["pos_rank"] = gold_area.groupby(["report_period_label","cluster","comparison_type"])["variance_abs"].rank(ascending=False, method="dense")
gold_area["neg_rank"] = gold_area.groupby(["report_period_label","cluster","comparison_type"])["variance_abs"].rank(ascending=True, method="dense")
gold_area = gold_area[["observation_id","report_period_label","period_scope","cluster","page_title","page_subtitle",
                       "page_subtitle_detail","comparison_type","entity_label","actual_value","base_value",
                       "variance_abs","variance_pct","rank_sign","pos_rank","neg_rank"]]

atomic.to_csv(OUTDIR / "silver_atomic_canonical_from_final.csv", index=False)
fact.to_csv(OUTDIR / "silver_business_fact_from_final.csv", index=False)
semantic.to_csv(OUTDIR / "silver_semantic_long_from_final.csv", index=False)
gold_overview.to_csv(OUTDIR / "gold_overview_from_final.csv", index=False)
gold_moves.to_csv(OUTDIR / "gold_country_product_moves_from_final.csv", index=False)
gold_area.to_csv(OUTDIR / "gold_area_products_from_final.csv", index=False)