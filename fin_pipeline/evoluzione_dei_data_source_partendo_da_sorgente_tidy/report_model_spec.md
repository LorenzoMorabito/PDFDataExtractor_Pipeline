# Target output model from df_canonical_FEB_2026.csv

## Recommended layers

### 1) silver_atomic_canonical.csv
Canonical metric table, still atomic:
- one row per metric observation
- preserves lineage and source metadata
- useful for audit/debug

### 2) silver_business_fact.csv
Recommended base table for report engineering:
- one row per business observation
- actual / budget / previous year aligned on the same row
- variances already reconstructed as columns
- best table for building gold views

Key columns:
- report_period_label
- page_title / page_subtitle / page_subtitle_detail
- chapter_name / subchapter_name
- period_scope
- section_family
- cluster
- entity_type
- entity_label
- actual_value
- budget_value
- py_actual_value
- variance_vs_budget_abs / variance_vs_budget_pct
- variance_vs_py_abs / variance_vs_py_pct

### 3) silver_semantic_long.csv
Comparison-ready tidy table:
- one row per business observation x comparison_type
- comparison_type in {PY, BDG}
- actual_value, base_value, variance_abs, variance_pct

Best for:
- ranking
- filters
- drill-through
- generic widgets

### 4) gold_overview.csv
Overview-serving dataset for:
- group overview
- BU
- region

### 5) gold_country_product_moves.csv
Serving dataset for:
- positive / negative country deviations
- positive / negative product deviations

### 6) gold_area_products.csv
Serving dataset for:
- WE / BC_TURKEY / APAC / LATAM / MEA product pages

### 7) silver_collision_audit.csv
Audit of ambiguous bundles that need parser fixes or mapping rules.
