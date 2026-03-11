import numpy as np
import pandas as pd


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
