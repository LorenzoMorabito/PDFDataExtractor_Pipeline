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
2) Installa la libreria `pdfdataextractor`:
   - Da repo git (consigliato):
     - `pip install git+https://<your_git_host>/<org>/PDFDataExtractor-lib.git@<tag>`
   - Da percorso locale:
     - `pip install -e ..\PDFDataExtractor-lib`

## Esecuzione
- Script: `run_pipeline.py`
- Config: `configs/pipeline/pipeline_config.json`

## Databricks
- Usa un Repo Databricks con questo progetto.
- In un notebook:
  - `%pip install -r requirements.txt`
  - `%pip install git+https://<your_git_host>/<org>/PDFDataExtractor-lib.git@<tag>`
- Esegui `run_pipeline.py` o importa `pipeline.etl_runner`.
