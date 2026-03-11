import numpy as np
import pandas as pd

from ..StartDate import StartDate


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
