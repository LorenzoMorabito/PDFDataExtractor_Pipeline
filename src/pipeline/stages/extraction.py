from pathlib import Path

from pdfdataextractor import extract_table_pages
from pdfdataextractor.config import load_config, validate_page_config

from ..contracts import ExtractionOutput


def _resolve_path(project_root: Path, value: str | Path) -> Path:
    p = Path(value)
    if p.is_absolute():
        return p
    return (project_root / p).resolve()


def extract_raw(config: dict, project_root: Path | None = None) -> ExtractionOutput:
    project_root = project_root or Path(__file__).resolve().parents[2]
    config_path = _resolve_path(project_root, config["extraction_config_path"])
    extraction_cfg = load_config(config_path)

    pdf_path = _resolve_path(project_root, extraction_cfg["pdf_path"])
    page_config = validate_page_config(extraction_cfg["page_config"])
    threshold_righe = float(extraction_cfg.get("threshold_righe", 2))

    extractor_cfg = config.get("extractor", {})
    result = extract_table_pages(
        pdf_path,
        page_config=page_config,
        threshold_righe=threshold_righe,
        return_phrases=bool(extractor_cfg.get("return_phrases", False)),
        return_stats=bool(extractor_cfg.get("return_stats", False)),
        return_log=bool(extractor_cfg.get("return_log", False)),
        return_lineage=bool(extractor_cfg.get("return_lineage", False)),
        return_cells=bool(extractor_cfg.get("return_cells", False)),
    )

    return ExtractionOutput(
        tables=result["tables"],
        page_config=page_config,
        extraction_cfg=extraction_cfg,
        raw_result=result,
    )
