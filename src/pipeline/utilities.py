import math
from loguru import logger


def is_empty(x):
    if x is None:
        return True
    if isinstance(x, float) and math.isnan(x):
        return True
    s = str(x).strip()
    return s == "" or s.lower() == "nan"


def norm(x):
    """ Normalizzazione base della cella """
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    s = str(x).strip()
    return "" if s.lower() == "nan" else s


def norm_str(x):
    return "" if is_empty(x) else str(x).strip()


def empty_ratio_row(row):
    return sum(is_empty(v) for v in row) / len(row)


def looks_like_header(row, HEADER_TOKENS, threshold_remaining=1, debug=False, numeric_threshold=0.5):
    """ Verifica se una riga ha le caratteristiche di un'intestazione (Set Theory) """
    # Nota: assume che is_empty sia definita o usa un controllo base
    raw_values = [str(v).strip().lower() for v in row if v is not None and str(v).strip().lower() != 'nan' and str(v).strip() != ""]
    
    if not raw_values:
        return False

    def is_numeric_simple(s):
        clean = s.replace('%','').replace(',','').replace('.','').replace('-','')
        return clean.isdigit()

    numeric_count = sum(1 for v in raw_values if is_numeric_simple(v))
    ratio = numeric_count / len(raw_values)
    
    if ratio > numeric_threshold:
        return False

    # Splittiamo i valori per gestire celle composte (es. "ACT vs BDG")
    row_tokens = set([part for val in raw_values for part in str(val).split(' ')])
    known_set = {t.lower().strip() for t in HEADER_TOKENS}
    remaining_tokens = row_tokens - known_set
    
    is_header = len(remaining_tokens) <= threshold_remaining
    
    if debug:
        logger.debug(f'[DEBUG] Row Tokens: {row_tokens} | Remaining: {remaining_tokens} | IS_HEADER: {is_header}')
        logger.debug(
            "looks_like_header: is_header={} ratio={:.3f} remaining_tokens={}",
            is_header,
            ratio,
            remaining_tokens,
        )
    
    return is_header


def recupera_livello_aggregazione(df, keywords, column_lookup, new_column_name):
    mask = df[column_lookup].isin(keywords)
    df[new_column_name] = df[column_lookup].where(mask).ffill()
    #df.drop(df[mask].index, inplace=True)
    return df