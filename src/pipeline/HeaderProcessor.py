import numpy as np
from collections import Counter
from .utilities import looks_like_header, norm
from loguru import logger

class HeaderProcessor:
    def __init__(self, header_tokens, name_overrides=None, rules=None, debug=False):
        self.tokens = header_tokens
        self.debug = debug

        # ---- Rule engine (Opzione A)
        # rules: lista di regole dichiarative
        self.rules = rules[:] if rules else []

        # Backward compatibility: name_overrides -> regole PRE
        if name_overrides:
            for idx, val in name_overrides.items():
                self.rules.append({
                    "id": f"legacy_override_{idx}",
                    "stage": "pre",
                    "type": "set_colname",
                    "col_idx": idx,
                    "value": val,
                    "when": {"op": "always"}
                })

        self.fallback = []
        self.fallback_page_ref = None

    # ---------------------------
    # 1) FILL BASE
    # ---------------------------
    def _fill_right(self, row):
        row = [norm(x) for x in row]
        for i in range(len(row)-2, -1, -1):
            if row[i] == "" and row[i+1] != "":
                row[i] = row[i+1]
        return row

    def _fill_left(self, row):
        row = [norm(x) for x in row]
        for i in range(1, len(row)):
            if row[i] == "" and row[i-1] != "":
                row[i] = row[i-1]
        return row

    def _score_header(self, row):
        row = [norm(x) for x in row]
        empties  = sum(1 for x in row if x == "")
        switches = sum(1 for i in range(1, len(row)) if row[i] != row[i-1])
        end_empty = 1 if row and row[-1] == "" else 0
        return empties*100 + switches*2 + end_empty*50

    def smart_fill(self, row):
        r1 = self._fill_right(row)
        r2 = self._fill_left(row)
        s1, s2 = self._score_header(r1), self._score_header(r2)
        if self.debug:
            logger.debug(f'SmartFill Score | Right={s1}, Left={s2}')
            logger.debug(f'SmartFill Result | Right={r1}')
            logger.debug(f'SmartFill Result | Left={r2}')
        return r1 if s1 < s2 else r2

    # -----------------------------------------
    # 2) NGRAM BLOCKS
    # -----------------------------------------
    def _token_class(self, t: str) -> str:
        """
        Classificazione leggera e robusta: serve per trovare pattern anche se cambia il testo.
        """
        t = norm(t).strip().lower()
        if not t:
            return "EMPTY"
        # YEAR
        if t.isdigit() and len(t) == 4:
            return "YEAR"
        # PCT
        if t in {"%", "pct", "percent"}:
            return "PCT"
        # UNIT
        if "/000" in t or "euro/000" in t or "k€" in t or "k eur" in t or "mn" in t:
            return "UNIT"
        # CUR
        if "eur" in t or "€" in t or "usd" in t or "$" in t or "gbp" in t:
            return "CUR"
        return "TXT"

    def _token_ngrams(self, seq, n: int):
        return [(tuple(seq[i:i+n]), i) for i in range(len(seq)-n+1)]

    def _find_repeated_ngram_blocks(self, seq, n=2, min_count=2):
        grams = self._token_ngrams(seq, n)
        counts = Counter(g for g, _ in grams)
        repeated = {g for g, c in counts.items() if c >= min_count}
        blocks = [(i, i+n-1, g) for g, i in grams if g in repeated]
        return blocks

    def _remove_overlap(self, blocks):
        out = []
        last_end = -1
        for a, b, pat in sorted(blocks, key=lambda x: x[0]):
            if a > last_end:
                out.append((a, b, pat))
                last_end = b
        return out

    def _pattern_priority(self, pat_tuple):
        s = set(pat_tuple)
        if "PCT" in s and "CUR" in s:
            return 3
        if "PCT" in s:
            return 2
        if "CUR" in s:
            return 1
        return 0

    def _score_blocks_against_row1(self, row1_raw, blocks_no_overlap):
        """
        Score guidato da contesto row1:
        - premia quanti vuoti vengono coperti e sono riempibili
        - penalizza blocchi ambigui (più di una label non vuota dentro)
        """
        r1 = [norm(x) for x in row1_raw]
        empty_idx = {i for i, x in enumerate(r1) if x == ""}

        fillable = 0
        covered_empty = 0
        ambiguity_penalty = 0

        for a, b, _ in blocks_no_overlap:
            empties_in_block = [i for i in range(a, b + 1) if i in empty_idx]
            if empties_in_block:
                covered_empty += len(empties_in_block)

            non_empty_vals = {r1[i] for i in range(a, b + 1) if r1[i] != ""}
            if empties_in_block and non_empty_vals:
                fillable += len(empties_in_block)

            if len(non_empty_vals) > 1:
                ambiguity_penalty += (len(non_empty_vals) - 1) * 10

        return {
            "fillable_empties": fillable,
            "covered_empties": covered_empty,
            "ambiguity_penalty": ambiguity_penalty
        }

    def _select_best_blocks_contextual(self, row1_raw, row2_raw, min_count=2, max_n=4):
        sig2 = [self._token_class(x) for x in row2_raw]
        L = len(sig2)

        best_key = None
        best_blocks = []
        best_meta = {"signature": sig2, "chosen": None, "blocks": [], "coverage_ratio": 0.0}

        # ------------------------------------------------------------------
        # Fallback "structural": se esiste una coppia adiacente CUR,PCT,
        # considerala come blocco anche se non è ripetuta (min_count non aiuta).
        # La applichiamo SOLO se serve davvero a riempire vuoti in row1_raw.
        # ------------------------------------------------------------------
        curpct_starts = [i for i in range(max(0, L - 1)) if sig2[i] == "CUR" and sig2[i + 1] == "PCT"]
        if curpct_starts:
            forced_blocks = [(i, i + 1, ("CUR", "PCT")) for i in curpct_starts]
            forced_blocks_no = self._remove_overlap(forced_blocks)
            forced_ctx = self._score_blocks_against_row1(row1_raw, forced_blocks_no)

            forced_coverage = len(forced_blocks_no) * 2
            forced_coverage_ratio = forced_coverage / max(1, L)

            # Applica il forced blocco solo se riempie almeno un vuoto reale di row1
            if forced_ctx["fillable_empties"] > 0:
                forced_meta = {
                    "signature": sig2,
                    "chosen": {"ngram": ("CUR", "PCT"), "n": 2, "forced": True},
                    "coverage_ratio": forced_coverage_ratio,
                    "blocks": forced_blocks_no,
                    "ctx": forced_ctx,
                    "key": ("forced_cur_pct", forced_ctx["fillable_empties"], forced_coverage)
                }
                return forced_blocks_no, forced_meta

        for n in range(2, min(max_n, L) + 1):
            grams = self._token_ngrams(sig2, n)
            counts = Counter(g for g, _ in grams)
            repeated = [g for g, c in counts.items() if c >= min_count]
            if not repeated:
                continue

            for pat in repeated:
                blocks = [(i, i + n - 1, pat) for g, i in grams if g == pat]
                blocks_no = self._remove_overlap(blocks)

                coverage = len(blocks_no) * n
                coverage_ratio = coverage / max(1, L)
                prio = self._pattern_priority(pat)

                ctx = self._score_blocks_against_row1(row1_raw, blocks_no)

                key = (
                    ctx["fillable_empties"],
                    coverage,
                    prio,
                    -ctx["ambiguity_penalty"],
                    n
                )

                if best_key is None or key > best_key:
                    best_key = key
                    best_blocks = blocks_no
                    best_meta = {
                        "signature": sig2,
                        "chosen": {"ngram": pat, "n": n},
                        "coverage_ratio": coverage_ratio,
                        "blocks": blocks_no,
                        "ctx": ctx,
                        "key": key
                    }

        return best_blocks, best_meta

    def _fill_row1_with_blocks(self, row1_current, block_ranges, row1_original=None):
        """
        Fill confinato: riempi solo i vuoti dentro ogni blocco.
        """
        cur = [norm(x) for x in row1_current]
        orig = [norm(x) for x in (row1_original if row1_original is not None else row1_current)]
        for a, b in block_ranges:
            anchor = next((orig[i] for i in range(a, b + 1) if orig[i] != ""), "")
            if not anchor:
                anchor = next((cur[i] for i in range(a, b + 1) if cur[i] != ""), "")
            if anchor:
                for i in range(a, b + 1):
                    if orig[i] == "":
                        cur[i] = anchor
        return cur

    # -----------------------------------------
    # 3) BUILD + SCORE
    # -----------------------------------------
    def _build_final_names(self, row1_filled, row2_raw):
        # merge
        names = []
        for token_r1, token_r2 in zip(row1_filled, row2_raw):
            token_r1_norm, token_r2_norm = norm(token_r1), norm(token_r2)
            if token_r2_norm and token_r1_norm:     names.append(f"{token_r2_norm} {token_r1_norm}")
            elif token_r2_norm:                     names.append(token_r2_norm)
            elif token_r1_norm:                     names.append(token_r1_norm)
            else:                                   names.append("")

        # normalize
        final_names = [
            n.lower().replace(" ", "_").replace("%", "pct") if n != "" else f"col_{i}"
            for i, n in enumerate(names)
        ]
        # APPLY RULES (PRE)
        final_names = self._apply_rules(final_names, stage="pre")
        return final_names

    def _score_final_names(self, final_names):
        """
        Score semplice ma efficace:
        - duplicati pesano tantissimo (errori semantici)
        - colonne col_i (vuote) pesano
        """
        dup = len(final_names) - len(set(final_names))
        empties = sum(1 for x in final_names if x.startswith("col_"))
        return dup * 1000 + empties * 50

    # -----------------------------------------
    # RULE ENGINE (Opzione A)
    # -----------------------------------------
    def _segments(self, name: str):
        return [p.lower() for p in str(name).split("_")]

    def _token_hits(self, names, tokens):
        tokens = {t.lower() for t in tokens}
        hit = []
        for i, n in enumerate(names):
            if any(seg in tokens for seg in self._segments(n)):
                hit.append(i)
        return hit

    def _apply_rules(self, names, stage: str):
        """
        Applica le regole dichiarative per lo stage richiesto (pre/post).
        Safety: se una regola genera duplicati, viene SKIPPATA.
        """
        out = list(names)

        for rule in self.rules:
            if rule.get("stage") != stage:
                continue

            rtype = rule.get("type")

            # ---- Rule: set_colname (override posizionale)
            if rtype == "set_colname":
                idx = int(rule.get("col_idx", -1))
                if idx < 0 or idx >= len(out):
                    continue

                when = rule.get("when", {"op": "always"})
                op = when.get("op", "always")

                if op == "always":
                    pass
                elif op == "col_segment_in":
                    tokens = when.get("tokens", [])
                    hit = self._token_hits(out, tokens)
                    if idx not in hit:
                        continue
                else:
                    continue

                candidate = out.copy()
                candidate[idx] = rule.get("value")

                if len(candidate) != len(set(candidate)):
                    continue

                out = candidate

            # ---- Rule: replace_segment (period placeholder generalizzato)
            elif rtype == "replace_segment":
                tokens = rule.get("tokens", [])
                placeholder = rule.get("placeholder")
                min_hits = int(rule.get("min_hits", 2))

                hit = self._token_hits(out, tokens)
                if len(hit) < min_hits:
                    continue

                candidate = out.copy()
                for i in hit:
                    parts = candidate[i].split("_")
                    candidate[i] = "_".join(
                        placeholder if p.lower() in {t.lower() for t in tokens} else p
                        for p in parts
                    )

                if len(candidate) != len(set(candidate)):
                    continue

                out = candidate

        return out

    # -----------------------------------------
    # 4) API PUBBLICHE (rinomina + estrai)
    # -----------------------------------------
    def rinomina_colonne(self, df, nomi_col_old, nomi_col_new, page_ref):
        logger.info("Inizio rinominare colonne")
        logger.debug(f"Header da sostituire={nomi_col_old}")
        logger.debug(f"Header nuovo={nomi_col_new}")

        if not nomi_col_new:
            logger.warning("Necessario Fallback nuovo Header non trovato")

            if self.fallback:
                if len(nomi_col_old) == len(self.fallback):
                    if page_ref == self.fallback_page_ref:
                        nomi_col_new = self.fallback
                        logger.warning(f"Fallback: {nomi_col_new}")
                    else:
                        logger.error(
                            'Il FallBack appartiene a una pagina diversa: ActualPage=[{}] | FallbackPage=[{}]',
                            page_ref, self.fallback_page_ref
                        )
                else:
                    logger.error(
                        'Il Fallback e il Vecchio Header non hanno la stessa lunghezza: OldHeader Length=[{}] | Fallback Length=[{}]',
                        len(nomi_col_old), len(self.fallback)
                    )
            else:
                logger.error('Nessun Fallback trovato per la pagina: PageRef=[{}]', page_ref)

        if len(nomi_col_old) != len(nomi_col_new):
            raise ValueError("Lunghezze non compatibili per rinomina colonne")

        df.rename(columns=dict(zip(nomi_col_old, nomi_col_new)), inplace=True)
        logger.info("Fine rinominare colonne [CORRETTO]")
        return df

    def estrai_nomi_colonne(
        self,
        df, col_indices, row1_idx, row2_idx, page_ref,
        drop_row=False, debug=None,
        period_placeholder: str = None,
        period_tokens=("december", "ytd"),
        period_min_hits: int = 2):

        old_debug = None
        if debug is not None:
            old_debug = self.debug
            self.debug = debug

        try:
            logger.info("Inizio elaborazione header")

            # --- Estrazione righe (label-based sulle colonne) ---
            try:
                cols = list(col_indices)
                row_1_raw = df.iloc[row1_idx][cols].tolist()
                row_2_raw = df.iloc[row2_idx][cols].tolist()
                logger.debug("Riga 1: " + str(row_1_raw))
                logger.debug("Riga 2: " + str(row_2_raw))
            except Exception as exc:
                logger.error("Errore estrazione righe header: {}", exc)
                if df is None or df.empty:
                    return np.nan, []
                return np.nan, []

            # Validazione
            if not (looks_like_header(row_1_raw, self.tokens, debug=self.debug)
                    and looks_like_header(row_2_raw, self.tokens, debug=self.debug)):
                logger.error("[ERRORE] Le righe non possono essere convertite in Header")
                return np.nan, []

            # Fail-fast: lunghezze coerenti
            if len(row_1_raw) != len(row_2_raw):
                logger.error("[ERRORE] Lunghezze diverse Row1={} Row2={}", len(row_1_raw), len(row_2_raw))
                return np.nan, []

            logger.info("Righe valide per essere convertite in Header")

            # --- Candidato A: smart_fill classico ---
            logger.info("Inizio Smart Filling")
            row1_smart = self.smart_fill(row_1_raw)
            names_smart = self._build_final_names(row1_smart, row_2_raw)
            score_smart = self._score_final_names(names_smart)
            logger.debug(f"Header score smart=[{score_smart}] | SmartHeader={names_smart}")


            # --- Candidato B: block-fill guidato da n-gram su row2 ---
            logger.info("Inizio N-gram Filling")
            
            blocks, meta = self._select_best_blocks_contextual(row_1_raw, row_2_raw, min_count=2, max_n=4)
            if blocks and (meta.get("ctx", {}).get("fillable_empties", 0) > 0 or meta.get("coverage_ratio", 0.0) >= 0.40):
                block_ranges = [(a, b) for a, b, _ in blocks]
                
                # ibrido: prima smart_fill (per i buchi "generali"), poi correzione confinata sui blocchi
                row1_block = self._fill_row1_with_blocks(row1_smart, block_ranges, row1_original=row_1_raw)
                names_block = self._build_final_names(row1_block, row_2_raw)
                score_block = self._score_final_names(names_block)
                logger.debug(f"Header score N-gram=[{score_block}] | N-gramHeader={names_block}")
            else:
                row1_block, names_block, score_block = None, None, float("inf")

            # --- Selezione best ---
            # Nota: _score_final_names oggi discrimina solo duplicati/col_i.
            # In caso di pareggio (0 vs 0) scegliamo il block se è "informativo":
            # - forced=True (fallback strutturale)
            # - oppure ha riempito vuoti reali (fillable_empties > 0)
            # - oppure copertura molto alta (coverage_ratio >= 0.60)
            forced = bool(meta.get("chosen", {}).get("forced")) if blocks else False
            fillable = int(meta.get("ctx", {}).get("fillable_empties", 0)) if blocks else 0
            coverage_ratio = float(meta.get("coverage_ratio", 0.0)) if blocks else 0.0

            use_block = False
            if score_block < score_smart:
                use_block = True
            elif (
                score_block == score_smart
                and score_block != float("inf")
                and names_block
                and names_block != names_smart
                and (forced or fillable > 0 or coverage_ratio >= 0.60)
            ):
                use_block = True

            final_names = names_block if use_block else names_smart
            row_1_filled = row1_block if use_block else row1_smart

            if self.debug:
                logger.debug(f"Header score smart={score_smart} block={score_block} use_block={use_block}")
                logger.debug(
                    f"Header score smart={score_smart} block={score_block} "
                    f"forced={forced} fillable={fillable} coverage={coverage_ratio:.2f} "
                    f"use_block={use_block}"
                )
                if blocks:
                    logger.debug(f"Blocks meta={meta}")
                # meta è utile anche quando blocks è vuoto (chosen=None)
                logger.debug(f"Blocks meta={meta}")

            period_ref = row_1_filled[0]

            # Backward compatibility: period_placeholder -> rule POST temporanea
            if period_placeholder:
                if not any(r.get("id") == "legacy_override_placeholder" for r in self.rules):
                    self.rules.append({
                        "id": "legacy_override_placeholder",
                        "stage": "post",
                        "type": "replace_segment",
                        "tokens": list(period_tokens),
                        "placeholder": period_placeholder,
                        "min_hits": period_min_hits
                    })

            # APPLY RULES (POST)
            final_names = self._apply_rules(final_names, stage="post")


            if drop_row:
                df.drop(index=df.index[[row1_idx, row2_idx]], inplace=True)
                df.reset_index(drop=True, inplace=True)

            self.fallback = final_names
            self.fallback_page_ref = page_ref
            logger.debug(f"Header={final_names}")
            logger.info("Fine elaborazione Header")
            return period_ref, final_names

        finally:
            if old_debug is not None:
                self.debug = old_debug
