# PDFDataExtractor Pipeline

Pipeline di trasformazione e qualità dati basata su `pdfdataextractor`.
Progettata per uso in Databricks (repo + notebook).

## Struttura
- `src/pipeline/`: moduli della pipeline (codice)
- `src/pipeline/stages/`: macromoduli (extraction, reconstruction, canonicalization, publish)
- `src/pipeline/domains/`: logiche di dominio riallocate (reconstruction, canonicalization)
- `src/pipeline/common/`: utility condivise
- `run_pipeline.py`: entrypoint di esecuzione
- `configs/`: configurazioni estrazione e pipeline
- `notebooks/`: notebook di analisi/test
- `data/raw/`: PDF di esempio (input)
- `artifacts/`: QC e monitoring (artefatti)
 - `scripts/`: check architetturale e regression harness

## Setup locale
1) Crea un virtualenv Python 3.11 (consigliato: `.venv311-dev`) e installa le dipendenze:
   - `pip install -r requirements.txt`
2) La libreria `pdfdataextractor` e' inclusa in `requirements.txt` come wheel locale.
   Se vuoi usare una versione da Git tag o da Volume Databricks, sostituisci la riga
   con il path/URL corretto.

## Esecuzione
- Script: `run_pipeline.py`
- Config: `configs/pipeline/pipeline_config_*.json`
- Esempio:
  - `python run_pipeline.py --config configs/pipeline/pipeline_config_DEC.json`
  - `python run_pipeline.py --config configs/pipeline/pipeline_config_GEN.json --output-dir data/output`

### Config Databricks vs locale
- Config Databricks ufficiale: `configs/pipeline/pipeline_config_DEC.json`
- Config locale condivisa: `configs/pipeline/pipeline_config_DEC.local.sample.json`
- Override personale opzionale: copia della sample in `configs/pipeline/pipeline_config_DEC.local.json`

Regola pratica:
- i file `*.local.sample.json` restano versionati e condivisi
- i file `*.local.json` sono ignorati da Git e servono solo per override macchina-specifici

Esempi:
- Smoke locale condiviso:
  - `python scripts/smoke_run.py --config configs/pipeline/pipeline_config_DEC.local.sample.json`
- Run locale con override personale:
  - `python run_pipeline.py --config configs/pipeline/pipeline_config_DEC.local.json`
- Run Databricks / config ufficiale:
  - `python run_pipeline.py --config configs/pipeline/pipeline_config_DEC.json`

Variabili ambiente supportate:
- `PIPELINE_CONFIG` (default: `configs/pipeline/pipeline_config_DEC.json`)
- `PIPELINE_OUTPUT_DIR` (override path output)
- `LOG_LEVEL` (default: `INFO`)

## Output
Output canonico:
- **Delta table** (`output.table_name`)

Artefatti QC/monitoring (file, relativi alla root del progetto):
- `qc_summary_path`
- `errors_path`
- `df_to_analyze_path` (scrive una directory CSV se non ha estensione)
- `log_percentage_path`
- `run_report_path`

Se `df_final_path` e' valorizzato, il file viene scritto; altrimenti si scrive solo la tabella.
Puoi disattivare la scrittura dei file con `--no-write`.

## Architettura
Macromoduli:
1. Extraction / Raw Acquisition: `pipeline.stages.extraction.extract_raw`
2. Table Reconstruction / Structural Parsing: `pipeline.stages.reconstruction.reconstruct_tables`
3. Canonicalization / Union / Data Quality: `pipeline.stages.canonicalization.canonicalize`
4. Publish / Persistence / Reporting: `pipeline.stages.publish.publish_outputs`

Orchestrazione end-to-end:
- `pipeline.orchestrator.run_pipeline`

Documentazione:
- `docs/ARCHITECTURE.md`
- `docs/REFACTOR_NOTES.md`

## Databricks
- Usa un Repo Databricks con questo progetto.
- Usa `databricks.yml` (bundle) per un job serverless Python script.
- Le dipendenze runtime sono definite in `databricks.yml` (environment serverless).
- `requirements.txt` e' solo per sviluppo locale, non per il job Databricks.

## Check e test
- Architettura: `python scripts/check_architecture.py`
- Smoke locale: `python scripts/smoke_run.py --config configs/pipeline/pipeline_config_DEC.local.sample.json`
- Regressione:
  - `python scripts/regression_check.py --config artifacts/_baseline_config_DEC.json --write-baseline`
  - `python scripts/regression_check.py --config artifacts/_baseline_config_DEC.json`
