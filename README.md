# PDFDataExtractor Pipeline

Pipeline di trasformazione e qualità dati basata su `pdfdataextractor`.
Progettata per uso in Databricks (repo + notebook).

## Struttura
- `src/pipeline/`: moduli della pipeline (codice)
- `run_pipeline.py`: entrypoint di esecuzione
- `configs/`: configurazioni estrazione e pipeline
- `notebooks/`: notebook di analisi/test
- `data/raw/`: PDF di esempio (input)
- `data/output/`: output locali

## Setup locale
1) Crea un virtualenv e installa le dipendenze:
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

Variabili ambiente supportate:
- `PIPELINE_CONFIG` (default: `configs/pipeline/pipeline_config_DEC.json`)
- `PIPELINE_OUTPUT_DIR` (override path output)
- `LOG_LEVEL` (default: `INFO`)

## Output
La pipeline scrive gli artefatti in base alla sezione `output` del config:
- `df_final_path`
- `qc_summary_path`
- `errors_path`
- `df_to_analyze_path`
- `log_percentage_path`
- `run_report_path`

Se `output` non e' definito, `df_final` usa `output_excel` della extraction config.
Puoi disattivare la scrittura con `--no-write`.

## Databricks
- Usa un Repo Databricks con questo progetto.
- Usa `databricks.yml` (bundle) per un job di tipo Python script.
- Per `pdfdataextractor`, carica la wheel su Volume/Workspace e aggiorna
  `requirements.txt` con il path del file.
