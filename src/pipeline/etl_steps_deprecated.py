import numpy as np
import pandas as pd

from .common.StartDate import StartDate


def clean_percentage_smart(df, threshold=0.5, max_loss_ratio=0.1):
    valori_persi_log = []
    for col in df.columns:
        if df[col].dtype == "object":
            sample = df[col].dropna().astype(str)
            if sample.empty:
                continue

            percent_count = sample.str.contains("%", na=False).sum()
            percent_ratio = percent_count / len(sample)

            if percent_ratio < threshold:
                continue

            backup_column = df[col].copy()

            try:
                cleaned = (
                    backup_column.astype(str)
                    .str.replace("%", "", regex=False)
                    .str.replace(",", ".", regex=False)
                    .str.strip()
                )

                converted = pd.to_numeric(cleaned, errors="coerce") / 100

                mask_nuovi_nan = converted.isna() & backup_column.notna()
                nuovi_nulli_count = mask_nuovi_nan.sum()
                loss_ratio = nuovi_nulli_count / len(df)

                if loss_ratio <= max_loss_ratio:
                    if nuovi_nulli_count > 0:
                        rows_con_problemi = df[mask_nuovi_nan].index
                        for idx in rows_con_problemi:
                            valori_persi_log.append({
                                "column": col,
                                "index": idx,
                                "or_val": backup_column.loc[idx]
                            })
                    df[col] = converted
                else:
                    df[col] = backup_column
            except Exception:
                df[col] = backup_column
    return df, valori_persi_log


def fix_numeric_smart_scan(df, pre_scan_threshold=0.5, max_loss_ratio=0.1):
    for col in df.columns:
        if df[col].dtype == "object":
            series_clean = df[col].dropna().astype(str).str.strip()
            if series_clean.empty:
                continue

            potential_nums = series_clean.str.contains(r"\d", regex=True).sum()
            potential_ratio = potential_nums / len(series_clean)

            if potential_ratio < pre_scan_threshold:
                continue

            backup_column = df[col].copy()
            nulli_iniziali = backup_column.isna().sum()

            try:
                cleaned = (
                    backup_column.astype(str)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                converted = pd.to_numeric(cleaned, errors="coerce")

                nulli_finali = converted.isna().sum()
                nuovi_nulli = nulli_finali - nulli_iniziali
                loss_ratio = nuovi_nulli / len(df) if len(df) > 0 else 0

                if loss_ratio <= max_loss_ratio:
                    df[col] = converted
                else:
                    df[col] = backup_column
            except Exception:
                df[col] = backup_column
    return df


def build_page_map(capitoli):
    page_map = {}
    for cap_name, cap_data in capitoli.items():
        for sub_name, sub_range in cap_data["sottocapitoli"].items():
            sub_start, sub_end = sub_range
            for pg in range(sub_start, sub_end + 1):
                page_map[pg] = (cap_name, sub_name)
    return page_map


def apply_capitoli(df, capitoli):
    page_map = build_page_map(capitoli)
    serie_mappata = df["page_num"].map(page_map)
    df["capitolo"] = serie_mappata.str[0]
    df["sottocapitolo"] = serie_mappata.str[1]
    return df


def map_period_start(df, year_ref):
    distinct_period_start = df["period_agg"].unique()
    mapping_risultati = {}
    ultimo_valore_valido = pd.Timestamp.now().strftime("01/%m/%Y")

    for value in distinct_period_start:
        try:
            res = StartDate.trova_inizio_periodo(value, year_ref)
            if res is not None:
                ultimo_valore_valido = res
                mapping_risultati[value] = res
            else:
                mapping_risultati[value] = ultimo_valore_valido
        except Exception:
            mapping_risultati[value] = ultimo_valore_valido

    df["period_start"] = df["period_agg"].map(mapping_risultati)
    df["period_start"] = pd.to_datetime(df["period_start"], dayfirst=True)
    return df


def apply_period_desc(df):
    period_desc_mask = df["period_agg"].astype(str).str.lower().str.strip().isin(StartDate.MONTHS)
    df["period_desc"] = np.where(period_desc_mask, "MONTH", df["period_agg"])
    return df


def finalize_columns(df, ordered_columns):
    return df[ordered_columns]
