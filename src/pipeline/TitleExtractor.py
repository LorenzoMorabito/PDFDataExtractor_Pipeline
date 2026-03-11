import numpy as np
from loguru import logger
from .utilities import is_empty, norm_str

def estrai_titolo_pagina(df, data_column, empty_threshold=0.5, max_title_rows=3, drop_row=False, debug=False):

    
    logger.info(f'Inizio Estrazione Titolo')
    logger.debug(f"estrai_titolo_pagina: empty_threshold={empty_threshold} max_title_rows={max_title_rows} drop_row={drop_row}")
    idx_list = []
    for i, row in enumerate(df[data_column].itertuples(index=False, name=None)):
        empty_ratio = sum(is_empty(v) for v in row) / len(row)

        if empty_ratio >= empty_threshold:
            idx_list.append(i)
            logger.debug(f'Idx[{i}] | empty_ratio[{empty_ratio}] | row{row}')
        else:
            logger.debug(f'Idx[{i}] | empty_ratio[{empty_ratio}] | row{row}')
            logger.info(f'Titolo Non Trovato')
            break 
        if len(idx_list) >= max_title_rows:
            break

    titolo_parts = []
    for idx in idx_list:
        cells = [norm_str(v) for v in df.loc[idx, data_column].tolist()]
        text = " ".join([c for c in cells if c])
        if text:
            titolo_parts.append(text)

    titolo = " | ".join(titolo_parts).upper()
    if not titolo:
        titolo = np.nan  # "TITOLO NON TROVATO"
    
    if drop_row and idx_list:
        df.drop(index=idx_list, inplace=True)
        df.reset_index(drop=True, inplace=True)    
    
    logger.info(f"Titolo estratto: {titolo}")
    return titolo
