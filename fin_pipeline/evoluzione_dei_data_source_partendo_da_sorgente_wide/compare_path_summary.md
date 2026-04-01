# Confronto percorso `df_final` vs `df_canonical`

Pulizia applicata a `df_final_FEB_2026.xlsx`:
- righe iniziali: 1902
- duplicati esatti rimossi: 23
- righe completamente vuote rimosse: 4
- righe header/spurie rimosse: 4
- righe business residue: 1871

## Dataset generati dal percorso `df_final`
- silver_atomic_canonical_from_final.csv
- silver_business_fact_from_final.csv
- silver_semantic_long_from_final.csv
- gold_overview_from_final.csv
- gold_country_product_moves_from_final.csv
- gold_area_products_from_final.csv

## Sintesi confronto
| dataset                    |   from_final_rows |   from_canonical_rows |   common_observation_ids |   only_final_observation_ids |   only_canonical_observation_ids | schema_equal   |
|:---------------------------|------------------:|----------------------:|-------------------------:|-----------------------------:|---------------------------------:|:---------------|
| silver_business_fact       |              1871 |                  1825 |                      960 |                          512 |                              508 | True           |
| silver_semantic_long       |              3461 |                  3423 |                      950 |                          504 |                              518 | True           |
| gold_overview              |               108 |                   108 |                       26 |                           82 |                               82 | True           |
| gold_country_product_moves |               166 |                   176 |                      128 |                            0 |                               10 | True           |
| gold_area_products         |              2204 |                  2200 |                      732 |                          112 |                              114 | True           |
