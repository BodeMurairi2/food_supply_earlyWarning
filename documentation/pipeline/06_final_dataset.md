# Step 6 – Final dataset

**Script:** `pipeline/step06_build_dataset.py`
**Output:** `food_security_dataset.csv` (repository root)

## Shape

- **630 rows** = 30 districts × 21 years (2006–2026)
- **570 rows with a target** (2006–2024, every district, every year)
- **60 forecast rows** (2025–2026): features, no target
- **75 columns**: 4 keys, 5 target columns, 65 features, 1 metadata column (`price_level`)

## Columns

| Group | Columns | From |
|---|---|---|
| Keys | `year`, `province`, `district`, `district_pcode` | — |
| Target | `food_insecure_pct`, `risk_class`, `label_source`, `is_survey_year`, `last_survey_food_insecure_pct` | Step 1 |
| Rainfall | `rain_*` (11) | Step 2 |
| Temperature | `temp_*` (7) | Step 3 |
| Prices | `price_*` (10) + `price_level` | Step 4 |
| Agriculture | `sas_*` (37), from 2014 | Step 5 |

Each group is described in its step's document.

## Feature coverage (% of feature values present)

| Years | Coverage | Why |
|---|---|---|
| 2006–2008 | 28% | Climate only |
| 2009–2013 | 35–43% | Climate + prices |
| 2014–2016 | 61% | + SAS area, improved seed, fertilizer use, % sold (no yields or kg/ha) |
| 2017–2020 | 66–73% | + SAS yields and fertilizer kg/ha (no production totals for 2017–2019) |
| 2021–2026 | 98–99% | All sources |

## How to use it for the baseline

- **Target:** `risk_class` (classification) or `food_insecure_pct` (regression).
- **Features:** the `rain_*`, `temp_*`, `price_*`, `sas_*` columns, plus `last_survey_food_insecure_pct` and optionally `province` / `district` (one-hot).
- **Do not use as features:** `food_insecure_pct`, `risk_class`, `label_source`, `is_survey_year` (they are the answer or describe it).
- **Validation:** hold out a whole survey round (e.g. train ≤ 2018, test on 2021 and 2024) and report accuracy on `label_source == "cari_survey"` rows, because the other rows are estimates.
- **Missing values:** older years lack prices and SAS. Use a model that handles missing values (e.g. gradient boosting) or impute, and consider adding missing-indicator columns.
- **Forecasting:** train on 2006–2024 and predict the 2025 and 2026 rows.
