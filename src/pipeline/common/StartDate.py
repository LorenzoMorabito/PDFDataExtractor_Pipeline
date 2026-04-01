from datetime import date
import re
from loguru import logger


MONTHS = {
    # EN
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,

    # IT
    "gennaio": 1, "gen": 1,
    "febbraio": 2, "feb": 2,
    "marzo": 3, "mar": 3,
    "aprile": 4, "apr": 4,
    "maggio": 5, "mag": 5,
    "giugno": 6, "giu": 6,
    "luglio": 7, "lug": 7,
    "agosto": 8, "ago": 8,
    "settembre": 9, "set": 9,
    "ottobre": 10, "ott": 10,
    "novembre": 11, "nov": 11,
    "dicembre": 12, "dic": 12,
}

class StartDate:
    MONTHS = MONTHS

    @staticmethod
    def trova_inizio_periodo(period_ref, year_ref, formato_data="%d/%m/%Y"):
        s = str(period_ref).strip()
        token = re.split(r"[\s,/_-]+", s)[0].lower()

        if not s or token == "nan":
            logger.debug("Periodo vuoto o non valorizzato: {}", period_ref)
            raise ValueError(f"Periodo non valorizzato: {period_ref!r}")

        if token == "ytd":
            logger.debug("Periodo aggregato senza mese esplicito: {}", period_ref)
            raise ValueError(f"Periodo aggregato senza mese: {period_ref!r}")

        if token not in MONTHS:
            logger.warning("Mese non riconosciuto: {}", period_ref)
            raise ValueError(f"Mese non riconosciuto: {period_ref!r}")

        month = MONTHS[token]
        start = date(int(year_ref), month, 1).strftime(formato_data)
        logger.debug("trova_inizio_periodo: period_ref={} year_ref={} start={}", period_ref, year_ref, start)
        return start


def trova_inizio_periodo(period_ref, year_ref, formato_data="%d/%m/%Y"):
    return StartDate.trova_inizio_periodo(period_ref, year_ref, formato_data=formato_data)



