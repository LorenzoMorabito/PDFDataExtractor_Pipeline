# Configuration Reference

Reference for the JSON configuration files used by the pipeline.

This document exists because the project uses plain JSON, and standard JSON does not support inline comments.
Use this file as the "comment layer" for:

- `configs/pipeline/pipeline_config_*.json`
- `configs/extraction/extract_config_page_*.json`

The explanations below are based on the code paths that consume each parameter.

## How To Read This File

- Part 1: quick glossary for fast lookup
- Part 2: detailed explanation by section
- "Used by" always refers to the function that reads or applies the parameter
- File paths are repo-relative

## Config Files

Two JSON files work together:

1. Extraction config
   Used to tell `pdfdataextractor` which PDF to read and how many columns each target page contains.

2. Pipeline config
   Used to control reconstruction, canonicalization, output writing, and mapping logic.

Typical link:

- `pipeline_config_*.json` contains `extraction_config_path`
- `extract_config_*.json` contains `pdf_path`, `threshold_righe`, `page_config`

## Part 1: Glossary

### Extraction Config

| Parameter | Type | Required | Used by | Purpose |
| --- | --- | --- | --- | --- |
| `pdf_path` | string | yes | `pipeline.stages.extraction.extract_raw` | PDF input path |
| `output_excel` | string | no | `run_pipeline._build_output_paths` | fallback output path for `df_final` when `output.df_final_path` is missing |
| `threshold_righe` | number | no | `pipeline.stages.extraction.extract_raw`, then `pdfdataextractor.extract_table_pages` | phrase grouping threshold used by the extractor |
| `page_config` | object `{page_num: n_columns}` | yes | `pipeline.stages.extraction.extract_raw`, then `pdfdataextractor.extract_table_pages` | tells the extractor which pages contain tables and how many columns to cluster on each page |

### Pipeline Config

| Parameter | Type | Required | Used by | Purpose |
| --- | --- | --- | --- | --- |
| `extraction_config_path` | string | yes | `pipeline.stages.extraction.extract_raw`, `run_pipeline.main` | path to the extraction config JSON |
| `extractor.return_phrases` | bool | no | `pipeline.stages.extraction.extract_raw` | request phrase artifact from the extractor |
| `extractor.return_stats` | bool | no | `pipeline.stages.extraction.extract_raw` | request stats artifact from the extractor |
| `extractor.return_log` | bool | no | `pipeline.stages.extraction.extract_raw` | request extractor log artifact |
| `extractor.return_lineage` | bool | no | `pipeline.stages.extraction.extract_raw` | request lineage artifact |
| `extractor.return_cells` | bool | no | `pipeline.stages.extraction.extract_raw` | request cell artifact |
| `debug` | bool | no | `pipeline.stages.reconstruction.reconstruct_tables` | enables debug behavior in header reconstruction |
| `header_tokens` | list[string] | yes | `pipeline.stages.reconstruction.reconstruct_tables`, `pipeline.common.utilities.looks_like_header` | vocabulary used to recognize header rows |
| `header_rules` | list[object] | no | `pipeline.domains.reconstruction.HeaderProcessor` | rule-based column-name overrides |
| `period_placeholder` | string or null | no | `pipeline.domains.reconstruction.HeaderProcessor.estrai_nomi_colonne` | optional placeholder used in post-processing column names |
| `period_tokens` | list[string] | no | `pipeline.domains.reconstruction.HeaderProcessor.estrai_nomi_colonne` | tokens to match when `period_placeholder` is active |
| `period_min_hits` | integer | no | `pipeline.domains.reconstruction.HeaderProcessor.estrai_nomi_colonne` | minimum token hits required before applying the placeholder rule |
| `title.max_title_rows` | integer | yes | `pipeline.domains.reconstruction.TitleExtractor.estrai_titolo_pagina` | max number of sparse top rows considered title/subtitle |
| `title.drop_row` | bool | yes | `pipeline.domains.reconstruction.TitleExtractor.estrai_titolo_pagina` | remove title rows from the table after extraction |
| `title.debug` | bool | yes | `pipeline.domains.reconstruction.TitleExtractor.estrai_titolo_pagina` | title extraction debug logging |
| `split.empty_threshold` | number | yes | `pipeline.domains.reconstruction.TableSplitter.find_table_split_points` | empty-row ratio used to detect split zones |
| `split.confirm_header` | bool | yes | `pipeline.domains.reconstruction.TableSplitter.find_table_split_points` | require a valid header near a split point |
| `split.debug` | bool | yes | `pipeline.domains.reconstruction.TableSplitter.*` | split detection debug logging |
| `split.keywords_primary` | list[string] | yes | `pipeline.domains.reconstruction.TableSplitter.find_sections_by_keyword` | primary keywords for table splitting |
| `split.keywords_fallback` | list[string] | yes | `pipeline.domains.reconstruction.TableSplitter.find_sections_by_keyword` | fallback keywords when primary split logic finds nothing |
| `slicer.header_rows` | list[int] | yes | `pipeline.domains.reconstruction.TableSlicer.split_side_by_side_half` | rows used to compare left and right halves of a table |
| `slicer.sim_thresholds` | list[number] | yes | `pipeline.domains.reconstruction.TableSlicer.split_side_by_side_half` | similarity thresholds for the rows in `header_rows` |
| `slicer.debug` | bool | yes | `pipeline.domains.reconstruction.TableSlicer.split_side_by_side_half` | slicer debug logging |
| `aggregation_keywords` | list[string] | yes | `pipeline.common.utilities.recupera_livello_aggregazione` | labels that seed the forward-filled aggregation level |
| `static_column_list` | list[string] | yes | `pipeline.stages.reconstruction.reconstruct_tables` | non-measure columns kept in each reconstructed table |
| `audit_column_list` | list[string] | yes | `pipeline.stages.reconstruction.reconstruct_tables` | audit columns expected from the extractor output |
| `dataquality.preview_limit` | integer | yes | `pipeline.domains.canonicalization.DataQuality` | max number of problematic columns previewed in QC output |
| `dataquality.mutate` | bool | yes | `pipeline.domains.canonicalization.DataQuality.run` | choose whether problematic tables are removed in place or copied out |
| `cleaning.percent_threshold` | number | yes | `pipeline.transforms.cleaning.clean_percentage_smart` | minimum ratio of `%` values before a column is treated as percentage |
| `cleaning.percent_max_loss_ratio` | number | yes | `pipeline.transforms.cleaning.clean_percentage_smart` | max acceptable null increase after percentage conversion |
| `cleaning.numeric_pre_scan_threshold` | number | yes | `pipeline.transforms.cleaning.fix_numeric_smart_scan` | minimum ratio of numeric-looking values before numeric coercion is attempted |
| `cleaning.numeric_max_loss_ratio` | number | yes | `pipeline.transforms.cleaning.fix_numeric_smart_scan` | max acceptable null increase after numeric coercion |
| `capitoli` | object | yes | `pipeline.transforms.chapters.apply_capitoli` | map page numbers to business chapter and subchapter |
| `year_ref` | integer | yes | `pipeline.transforms.period.map_period_start` | year applied to recognized month labels in `period_agg` |
| `output.df_final_path` | string | no | `run_pipeline._build_output_paths`, `pipeline.stages.publish.publish_outputs` | optional explicit file path for final dataframe |
| `output.qc_summary_path` | string | no | `run_pipeline._build_output_paths`, `pipeline.stages.publish.publish_outputs` | QC summary output path |
| `output.errors_path` | string | no | `run_pipeline._build_output_paths`, `pipeline.stages.publish.publish_outputs` | errors output path |
| `output.df_to_analyze_path` | string | no | `run_pipeline._build_output_paths`, `pipeline.stages.publish.publish_outputs` | path for problematic tables export |
| `output.log_percentage_path` | string | no | `run_pipeline._build_output_paths`, `pipeline.stages.publish.publish_outputs` | path for percentage-conversion loss log |
| `output.run_report_path` | string | no | `run_pipeline._build_output_paths`, `pipeline.stages.publish.publish_outputs` | run summary JSON path |
| `output.table_name` | string or null | no | `pipeline.stages.publish.write_delta_table` | target Delta table name |
| `output.write_mode` | string | no | `pipeline.stages.publish.write_delta_table` | Spark write mode, usually `overwrite` |
| `final_columns` | list[string] | yes | `pipeline.transforms.final_transformation.finalize_columns` | final strict output column order |

## Part 2: Detailed Reference

### Extraction Config

#### `pdf_path`

- Purpose: points to the PDF to parse.
- Used by: `src/pipeline/stages/extraction.py::extract_raw`
- Behavior: relative paths are resolved against the project root; absolute paths are used as-is.
- How to set it: prefer repo-relative local paths such as `data/raw/F5_Book Net Sales February 2026.pdf` for local runs.
- Common mistake: leaving a Databricks `/Volumes/...` path in a local config.

#### `output_excel`

- Purpose: legacy fallback output path for the final dataframe.
- Used by: `run_pipeline.py::_build_output_paths`
- Behavior: only used when `output.df_final_path` is not defined and no `--output-dir` override is passed.
- How to set it: optional; for local work it is fine to point to `data/output/...xlsx`.
- Important: if you run with `--output-dir`, the CLI-generated CSV path wins and this field is ignored.

#### `threshold_righe`

- Purpose: controls phrase grouping sensitivity inside `pdfdataextractor`.
- Used by: `src/pipeline/stages/extraction.py::extract_raw`, then passed to `pdfdataextractor.extract_table_pages`
- How to set it: keep the established value unless phrase segmentation is clearly wrong.
- Typical value: `2`.

#### `page_config`

- Purpose: tells the extractor which pages to parse and how many columns to cluster on each page.
- Used by: `src/pipeline/stages/extraction.py::extract_raw`
- Downstream effect: passed into `pdfdataextractor`, where each `n_columns` value becomes `n_components` in a Gaussian Mixture clustering step.
- How to set it:
  - keys are 1-based PDF page numbers
  - values are expected table column counts
  - include only pages that actually contain a table
- Common mistakes:
  - copying another month without revalidating page layout
  - including title-only pages
  - setting more columns than the page actually exposes
- Typical failure when wrong:
  - `ValueError: Expected n_samples >= n_components`
  - this usually means a page is not tabular or the configured column count is too high

### Pipeline Config

#### `extraction_config_path`

- Purpose: links the pipeline config to its extraction config.
- Used by: `src/pipeline/stages/extraction.py::extract_raw`, `run_pipeline.py::main`
- How to set it: point to the matching extraction JSON for the same month/layout.

### `extractor`

These flags are passed to `pdfdataextractor.extract_table_pages` by `src/pipeline/stages/extraction.py::extract_raw`.

#### `extractor.return_phrases`

- Purpose: request phrase-level artifact output from the library.
- Practical note: not used by later pipeline stages today.

#### `extractor.return_stats`

- Purpose: request extraction stats artifact.
- Practical note: useful for debugging or future extensions, not consumed by the pipeline stages today.

#### `extractor.return_log`

- Purpose: request extractor log artifact.

#### `extractor.return_lineage`

- Purpose: request lineage artifact.

#### `extractor.return_cells`

- Purpose: request cell artifact.

For all `extractor.*` flags:

- Recommended default: `false` unless you are inspecting extractor internals.
- Reason: they increase payload size and are not used by reconstruction/canonicalization today.

#### `debug`

- Purpose: top-level reconstruction debug switch.
- Used by: `src/pipeline/stages/reconstruction.py::reconstruct_tables`
- Practical effect: passed mainly into `HeaderProcessor`; it does not globally enable debug for all modules.

### Header Reconstruction

#### `header_tokens`

- Purpose: defines the vocabulary that identifies header rows.
- Used by:
  - `src/pipeline/stages/reconstruction.py::reconstruct_tables`
  - `src/pipeline/common/utilities.py::looks_like_header`
- Behavior:
  - matching is case-insensitive
  - tokens are compared against split words from row text
  - too few matching tokens can make a header row look like data
- How to set it:
  - include month names used in the report
  - include structural words such as `act`, `bdg`, `eur`, `%`, `ytd`
- Common mistake: keeping `december` in a February config.

#### `header_rules`

- Purpose: deterministic overrides applied to generated column names.
- Used by: `src/pipeline/domains/reconstruction/HeaderProcessor.py::_apply_rules`
- Supported rule stages:
  - `pre`
  - `post`
- Supported rule types in current code:
  - `set_colname`
  - `replace_segment`
- Supported `when.op` values in current code:
  - `always`
  - `col_segment_in`
- Current examples:
  - force first column to `item_agg`
  - rename second column to `item_agg_2` when a month or `ytd` token is present
- Important:
  - rules that create duplicate names are skipped
  - unsupported rule shapes are silently ignored

#### `period_placeholder`

- Purpose: optional token replacement applied after column names are built.
- Used by: `src/pipeline/domains/reconstruction/HeaderProcessor.py::estrai_nomi_colonne`
- Behavior:
  - if non-null, the code dynamically injects a post rule of type `replace_segment`
  - replacement only happens if enough `period_tokens` are found
- When to use it: only if you want to normalize month-specific column segments into a shared placeholder.

#### `period_tokens`

- Purpose: token set used by the placeholder replacement logic.
- Used by: `src/pipeline/domains/reconstruction/HeaderProcessor.py::estrai_nomi_colonne`
- Behavior: matching is case-insensitive.

#### `period_min_hits`

- Purpose: minimum number of matching segments required before the placeholder replacement runs.
- Used by: `src/pipeline/domains/reconstruction/HeaderProcessor.py::_apply_rules`

### Title Extraction

#### `title.max_title_rows`

- Purpose: max number of sparse rows at the top of a table section that can be absorbed into title text.
- Used by: `src/pipeline/domains/reconstruction/TitleExtractor.py::estrai_titolo_pagina`

#### `title.drop_row`

- Purpose: if `true`, extracted title rows are removed from the dataframe before later steps.
- Used by: `src/pipeline/domains/reconstruction/TitleExtractor.py::estrai_titolo_pagina`

#### `title.debug`

- Purpose: enable title extraction logging.
- Used by: `src/pipeline/domains/reconstruction/TitleExtractor.py::estrai_titolo_pagina`

Important limitation:

- the title extractor also has an internal `empty_threshold`, but it is not exposed in JSON today
- the current fixed default is `0.5`

### Table Splitting

#### `split.empty_threshold`

- Purpose: minimum empty-cell ratio to classify a row as sparse for split detection.
- Used by: `src/pipeline/domains/reconstruction/TableSplitter.py::find_table_split_points`
- Higher values: fewer rows count as split markers.
- Lower values: more aggressive splitting.

#### `split.confirm_header`

- Purpose: require a likely header around a candidate split.
- Used by: `src/pipeline/domains/reconstruction/TableSplitter.py::find_table_split_points`
- Recommended default: keep `true` unless you are compensating for a badly structured PDF.

#### `split.debug`

- Purpose: enable split-detection logging.
- Used by: `src/pipeline/domains/reconstruction/TableSplitter.py`

#### `split.keywords_primary`

- Purpose: first keyword set used when sparse-row split detection finds nothing.
- Used by: `src/pipeline/domains/reconstruction/TableSplitter.py::find_sections_by_keyword`

#### `split.keywords_fallback`

- Purpose: second keyword set used as a final fallback.
- Used by: `src/pipeline/domains/reconstruction/TableSplitter.py::find_sections_by_keyword`
- Practical use: month labels and `YTD` often belong here.

Important limitation:

- `max_lookahead`, `min_rows_per_table`, and other keyword-split guardrails are coded in `TableSplitter.py` and are not exposed in JSON today

### Side-by-Side Table Slicing

#### `slicer.header_rows`

- Purpose: row indexes used to compare the left and right halves of a table.
- Used by: `src/pipeline/domains/reconstruction/TableSlicer.py::split_side_by_side_half`
- Typical value: `[0, 1]`

#### `slicer.sim_thresholds`

- Purpose: similarity thresholds for the rows in `header_rows`.
- Used by: `src/pipeline/domains/reconstruction/TableSlicer.py::split_side_by_side_half`
- Important:
  - the code zips `header_rows` and `sim_thresholds`
  - keep the same length for clarity and predictability

#### `slicer.debug`

- Purpose: enable slicer diagnostics.
- Used by: `src/pipeline/domains/reconstruction/TableSlicer.py::split_side_by_side_half`

### Aggregation and Structural Columns

#### `aggregation_keywords`

- Purpose: values in `item_agg` that seed the forward-filled `item_agg_1`.
- Used by: `src/pipeline/common/utilities.py::recupera_livello_aggregazione`
- Behavior: matching is exact, using `Series.isin(...)`.
- Common mistake: using labels that differ in capitalization, punctuation, or spacing from the real extracted values.

#### `static_column_list`

- Purpose: declares which structural columns must be preserved after reconstruction.
- Used by: `src/pipeline/stages/reconstruction.py::reconstruct_tables`
- Important:
  - these columns must exist by the time reconstruction appends the table
  - ordering matters because the stage builds `audit_cols + static_cols + dynamic_cols`

#### `audit_column_list`

- Purpose: declares which audit columns from the extractor output must be kept.
- Used by: `src/pipeline/stages/reconstruction.py::reconstruct_tables`
- Typical values: `run_id`, `timestamp_utc`

### Data Quality

#### `dataquality.preview_limit`

- Purpose: limit how many problematic column names are previewed in QC outputs.
- Used by: `src/pipeline/domains/canonicalization/DataQuality.py::DataQuality`

#### `dataquality.mutate`

- Purpose: choose how problematic reconstructed tables are separated from clean ones.
- Used by: `src/pipeline/domains/canonicalization/DataQuality.py::DataQuality.run`
- Behavior:
  - `false`: returns separate clean/problem lists without modifying the input list
  - `true`: removes problematic tables from the original list in place
- Recommended default: `false` for safer debugging.

Important limitation:

- suspicious token lists and regex behavior inside `DataQuality` are hard-coded today and not exposed in JSON

### Cleaning

#### `cleaning.percent_threshold`

- Purpose: minimum percentage of `%` strings required before a column is treated as a percentage column.
- Used by: `src/pipeline/transforms/cleaning.py::clean_percentage_smart`

#### `cleaning.percent_max_loss_ratio`

- Purpose: maximum allowed ratio of newly introduced nulls when converting percentages.
- Used by: `src/pipeline/transforms/cleaning.py::clean_percentage_smart`
- Behavior: if conversion loses too much data, the original column is restored.

#### `cleaning.numeric_pre_scan_threshold`

- Purpose: minimum ratio of numeric-looking values before generic numeric conversion is attempted.
- Used by: `src/pipeline/transforms/cleaning.py::fix_numeric_smart_scan`

#### `cleaning.numeric_max_loss_ratio`

- Purpose: maximum allowed ratio of newly introduced nulls when coercing numeric columns.
- Used by: `src/pipeline/transforms/cleaning.py::fix_numeric_smart_scan`

### Chapter Mapping

#### `capitoli`

- Purpose: map `page_num` to business chapter and subchapter.
- Used by: `src/pipeline/transforms/chapters.py::apply_capitoli`

Structure:

- top-level chapter name
- nested `sottocapitoli`
- each subchapter mapped to `[start_page, end_page]`

Important implementation detail:

- only `sottocapitoli` is actually used by the code today
- the sibling `page` field is descriptive only and is not read by `apply_capitoli`

Common mistake:

- updating the chapter-level `page` range and forgetting that the real behavior comes from the `sottocapitoli` ranges

### Period Mapping

#### `year_ref`

- Purpose: assign a year to recognized month labels in `period_agg`.
- Used by: `src/pipeline/transforms/period.py::map_period_start`
- Downstream helper: `src/pipeline/common/StartDate.py::StartDate.trova_inizio_periodo`
- Behavior:
  - recognized month labels become first-of-month dates in `period_start`
  - unrecognized labels such as `YTD` fall back to the last valid month seen and log an error

### Output

The `output` section is resolved by `run_pipeline.py::_build_output_paths` and written by `src/pipeline/stages/publish.py::publish_outputs`.

#### `output.df_final_path`

- Purpose: explicit path for the final dataframe.
- If omitted:
  - the CLI falls back to extraction `output_excel`
  - if `--output-dir` is passed, the CLI generates a CSV filename automatically

#### `output.qc_summary_path`

- Purpose: QC summary output path.

#### `output.errors_path`

- Purpose: errors output path.
- Note: if the suffix is `.json`, the writer emits line-delimited JSON records, not a pretty JSON array.

#### `output.df_to_analyze_path`

- Purpose: export problematic tables isolated by data quality checks.
- Behavior:
  - `.xlsx` or `.xls`: writes a multi-sheet workbook if possible
  - no suffix: writes a directory of CSV files
  - Excel write failure falls back to a CSV directory

#### `output.log_percentage_path`

- Purpose: records rows whose percentage conversion would otherwise lose values.

#### `output.run_report_path`

- Purpose: writes a compact run summary containing:
  - final dataframe shape
  - QC row count
  - error row count
  - number of `df_to_analyze` tables

#### `output.table_name`

- Purpose: Delta table target.
- Used by: `src/pipeline/stages/publish.py::write_delta_table`
- For local runs: usually set to `null`.

#### `output.write_mode`

- Purpose: Spark write mode used when `table_name` is set.
- Typical value: `overwrite`

### Final Schema

#### `final_columns`

- Purpose: strict final column order.
- Used by: `src/pipeline/transforms/final_transformation.py::finalize_columns`
- Important:
  - this is a hard subset operation: `return df[ordered_columns]`
  - if a listed column is missing, the pipeline fails with `KeyError`
  - if a column exists but is omitted here, it disappears from the final output

## Practical Recommendations

### For a new monthly PDF

1. Copy the nearest previous month config pair.
2. Update the month-specific tokens:
   - `header_tokens`
   - `period_tokens`
   - `split.keywords_fallback`
3. Update `year_ref`.
4. Rebuild `page_config`.
5. Remove title-only pages from `page_config`.

### For local runs

- prefer repo-relative paths
- keep `output.table_name = null`
- use `--output-dir data/output` when running from CLI

### For debugging extraction failures

Check first:

- `pdf_path`
- `page_config`
- month token consistency across:
  - `header_tokens`
  - `period_tokens`
  - `split.keywords_fallback`

Typical symptoms:

- `Expected n_samples >= n_components`
  - usually wrong `page_config`
- header conversion errors in reconstruction
  - often wrong month tokens or wrong page included
- missing `period_start`
  - often `year_ref` or `period_agg` mismatch

