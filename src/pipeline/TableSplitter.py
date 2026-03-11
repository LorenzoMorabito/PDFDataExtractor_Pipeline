from loguru import logger
import re
from .utilities import empty_ratio_row, looks_like_header

def group_consecutive(indices):
    blocks = []
    if not indices:
        return blocks
    start = prev = indices[0]
    for x in indices[1:]:
        if x == prev + 1:
            prev = x
        else:
            blocks.append((start, prev))
            start = prev = x
    blocks.append((start, prev))
    return blocks


def _row(df, data_cols, pos):
    return df.loc[:, data_cols].iloc[pos].tolist()

def backtrack_to_title(df, data_cols, p, empty_threshold, debug=False):
    """
    Se prima di p ci sono SOLO righe sparse (>= empty_threshold),
    sposta p indietro fino alla prima riga non sparse
    """
    if p <= 0:
        return p

    # se esiste una riga densa prima, non tocchiamo nulla
    for j in range(p - 1, -1, -1):
        row = _row(df, data_cols, j)
        row_empty_ratio = empty_ratio_row(row)
        if debug:
            logger.debug(f'Backtrack Check: j={j} | EmptyRatio={row_empty_ratio:.2f} | Row={row}')
        if row_empty_ratio < empty_threshold:
            # incontrata una riga non-sparse: stop, p resta com'è
            return p

    # se NON abbiamo incontrato righe dense, allora tutto il prefisso è sparse
    # backtrack fino all'inizio del run sparse che arriva a p
    j = p
    while j - 1 >= 0:
        prev_row = _row(df, data_cols, j - 1)
        if empty_ratio_row(prev_row) >= empty_threshold:
            j -= 1
        else:
            break
    return j


def backtrack_sparse_run_start(df, data_cols, p, empty_threshold):
    """
    Backtrack SOLO sul run di righe sparse immediatamente prima di p.
    Utile per includere titolo/sottotitolo che stanno subito sopra l'header.
    A differenza di backtrack_to_title, funziona anche se prima ci sono dati densi.
    """
    j = p
    while j - 1 >= 0:
        prev_row = _row(df, data_cols, j - 1)
        if empty_ratio_row(prev_row) >= empty_threshold:
            j -= 1
        else:
            break
    return j


def has_data_before(df, data_cols, pos, HEADER_TOKENS, empty_threshold, debug=False):
    """
    True se prima di 'pos' esiste almeno una riga che:
      - non è sparse (empty_ratio < empty_threshold)
      - e NON sembra un header
    Serve per evitare split all'inizio della tabella.
    """
    if pos <= 0:
        return False
    for j in range(pos - 1, -1, -1):
        row = _row(df, data_cols, j)
        if empty_ratio_row(row) < empty_threshold and (not looks_like_header(row, HEADER_TOKENS, debug=False)):
            return True
    return False


def find_sections_by_keyword(
    df,
    data_cols,
    HEADER_TOKENS,
    keywords=['TOTAL', 'GRAND_TOTAL'],
    max_lookahead=2,
    min_rows_per_table=5,
    empty_threshold=0.5,
    title_empty_threshold=0.85,
    debug=False,
):
    """
    Individua punti di split dopo una keyword, ma solo se segue un vero Header.
    """
    pattern = '|'.join(re.escape(k) for k in keywords)
    mask = df[data_cols].astype(str).apply(lambda x: x.str.contains(pattern, case=False, na=False)).any(axis=1)
    
    total_positons = [i for i, v in enumerate(mask.to_list()) if v]
    valid_split_points = []
    
    if debug:
        logger.info(f'Inizio Procedura di Split per Keywords')
        logger.debug(f'SplitPoint={valid_split_points}')
        logger.debug(f'HEADER_TOKENS={HEADER_TOKENS}')

    for current_pos in total_positons:
        # GUARDRAIL: se la keyword cade su una riga che sembra HEADER (es. December/YTD),
        # NON è un separatore di tabelle -> ignora questo hit.
        current_row = _row(df, data_cols, current_pos)
        if looks_like_header(current_row, HEADER_TOKENS, debug=debug):
            if debug:
                logger.debug(f"Skip keyword-hit on HEADER row at pos={current_pos} | Row={current_row}")
            continue

        # Guardrail 1: Lookahead - Cerchiamo un header nelle righe successive [Fino ad un massimo di max_lookhead]
        for offset in range(1, max_lookahead + 1):
            target_pos = current_pos + offset
            if target_pos < len(df):
                candidate_row = _row(df, data_cols, target_pos)
                
                if debug:
                    logger.debug(f'TargetPosition=[{target_pos}] | Row={candidate_row}')

                if looks_like_header(candidate_row, HEADER_TOKENS, debug=debug):
                    # Includi eventuali righe sparse subito sopra l'header (titolo)
                    candidate = backtrack_sparse_run_start(df, data_cols, target_pos, title_empty_threshold)
                    # Guardrail: se sopra candidate NON ci sono dati (solo titolo/header), non splittare
                    if not has_data_before(df, data_cols, candidate, HEADER_TOKENS, title_empty_threshold, debug=debug):
                        if debug:
                            logger.debug(f"Skip keyword split at candidate={candidate} (no data before; likely table start)")
                        break
                    if candidate > 0:
                        valid_split_points.append(candidate)
                    else:
                        # candidate==0 => split inutile (split_by_points scarta 0). Non aggiungere.
                        if debug:
                            logger.debug(f"Keyword split backtracked to 0 at target_pos={target_pos}; skip.")
                    break
                elif empty_ratio_row(candidate_row) < empty_threshold:
                    # Se troviamo dati densi che non contengono parole contenute nell'HEADER_TOKENS scarta indice
                    break 

    
    # Guardrail 2: Anti-Frammentazione
    if len(valid_split_points) > (len(df) / min_rows_per_table):
        # Teniamo solo gli split che distano almeno min_rows_per_table righe l'uno dall'altro
        filtered_points = []
        last_p = -min_rows_per_table
        for p in sorted(set(valid_split_points)):
            if p - last_p >= min_rows_per_table:
                filtered_points.append(p)
                last_p = p
        return filtered_points
    return valid_split_points


def find_table_split_points(df,
                            data_cols,
                            HEADER_TOKENS,
                            empty_threshold=0.85,
                            max_scan=None,
                            confirm_header=True,
                            debug=False,
                        ):
    """
    trova blocchi di righe molto vuote, scarta blocco iniziale, split dopo il blocco.
    Restituisce una lista di indici che rappresentano la riga di inizio di una o piu nuove tabelle
    """
    n = len(df) if max_scan is None else min(len(df), max_scan)

    sparse_idxs = []
    for i, row in enumerate(df[data_cols].itertuples(index=False, name=None)):
        if i >= n:
            break
        if empty_ratio_row(row) >= empty_threshold:
            sparse_idxs.append(i)

    blocks = group_consecutive(sparse_idxs)
    if not blocks:
        return []

    # scarta blocco iniziale
    if blocks[0][0] == 0:
        blocks = blocks[1:]

    split_points = []
    for (a, b) in blocks:
        candidate = b
        if candidate < len(df):
            candidate_row = df.loc[:, data_cols].iloc[candidate].tolist()
            if (not confirm_header) or looks_like_header(candidate_row, HEADER_TOKENS, debug=debug):
                split_points.append(candidate)

    # Guardrail: se uno split point ha SOLO righe sparse davanti (titoli),
    # allora eliminare lo split per non tagliare via il titolo dalla tabella.
    adjusted = []
    for p in split_points:
        p2 = backtrack_to_title(df, data_cols, p, empty_threshold, debug=debug)
        if p2 <= 0:
            if debug:
                logger.debug(f"drop split={p} -> backtrack={p2} (solo righe sparse prima, probabile titolo)")
            continue
        adjusted.append(p2)

    split_points = sorted(set(adjusted))

    logger.debug(
        "find_table_split_points: splits={} empty_threshold={} max_scan={}",
        split_points,
        empty_threshold,
        max_scan,
    )
    return split_points


def split_by_points(df, points, debug=False):
    """ Divide fisicamente il df usando i punti individuati e restituisce una lista contenente i df divisi"""
    points = sorted({p for p in points if 0 < p < len(df)})  # unici, validi
    cuts = [0] + points + [len(df)]
    out = []
    for s, e in zip(cuts[:-1], cuts[1:]):
        part = df.iloc[s:e].reset_index(drop=True)
        if debug:
            logger.debug(f"Splitting at {s}:{e}")
        if len(part) > 0:
            out.append(part)
    return out
