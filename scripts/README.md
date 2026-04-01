# Scripts

Questa cartella contiene controlli separati dalla pipeline runtime.

Uso previsto:
- si lanciano all'occorrenza durante sviluppo, verifica locale e prima del push
- non fanno parte dell'esecuzione standard di `run_pipeline.py`

Controlli disponibili:
- `check_architecture.py`: controlla che i confini tra orchestrator, stages, domains, transforms e common restino coerenti.
- `smoke_run.py`: esegue un run locale rapido end-to-end e verifica che la pipeline arrivi a produrre il `df_final`.
- `publish_check.py`: esegue un run locale e verifica che gli artifact finali vengano scritti correttamente.
- `regression_check.py`: confronta il risultato corrente con una baseline salvata e segnala differenze inattese.

Default attuali:
- gli script che leggono una config puntano di default a config locali o baseline locali
- per testare altri mesi o altri setup si puo sempre passare `--config`
