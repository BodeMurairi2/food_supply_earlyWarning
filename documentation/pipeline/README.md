# HarvestWatch data pipeline (baseline)

This pipeline builds **one modelling table**, `food_security_dataset.csv` at the repository root: one row per **district** per **year**, 2006 to 2026, with the food-security target and features from climate, prices and agriculture.

It is a **baseline**: every source is used in a simple, documented way so the table can be rebuilt and improved step by step.

## How to run

```bash
venv/bin/python pipeline/run_all.py          # all steps
venv/bin/python pipeline/step04_prices.py    # or a single step (run from anywhere)
```

Each step reads raw data from `data/`, writes its own CSV to `data/features/`, and prints a short summary. Step 6 merges them.

## Steps

| Step | Script | Output | What it adds | Doc |
|---|---|---|---|---|
| 1 | `step01_target.py` | `01_target.csv`, `01_target_survey_rounds.csv` | Target: % of households food insecure, 2006–2024 | [01_target.md](01_target.md) |
| 2 | `step02_rainfall.py` | `02_rainfall.csv` | 11 rainfall features (CHIRPS) | [02_rainfall.md](02_rainfall.md) |
| 3 | `step03_temperature.py` | `03_temperature.csv` | 7 temperature features (ERA5-Land) | [03_temperature.md](03_temperature.md) |
| 4 | `step04_prices.py` | `04_prices.csv` | 10 staple price features (WFP) | [04_prices.md](04_prices.md) |
| 5 | `step05_sas.py` + `sas_legacy.py` | `05_sas.csv` (+ 2 audit files) | 37 agriculture features (NISR SAS 2013–2025) | [05_sas.md](05_sas.md) |
| 6 | `step06_build_dataset.py` | `food_security_dataset.csv` | Merge of steps 1–5 | [06_final_dataset.md](06_final_dataset.md) |

Shared constants (district list, years, helpers) are in `pipeline/common.py`.

## Key design choices

- **Unit:** district × year. All 30 districts, each with its province (NISR gazetteer names, e.g. "Eastern Province").
- **Target year t** is the year a CFSVA survey would be collected (about April–May of t).
- **Features only use information from before the survey** (up to March of t), so the table can be used for forecasting:
  - rains and temperature of Season B (March–May of t-1) and Season A (September–December of t-1), and the 12 months March t-1 to February t
  - prices over April t-1 to March t
  - SAS harvests of Season B and C of t-1 and Season A of t (harvested January–February of t)
- **2025 and 2026 rows have features but no target**: these are the years to forecast.
- Every row says where its target came from (`label_source`): a real survey, an FCS-based estimate, or interpolation.

## Data sources

| Source | Folder | Coverage |
|---|---|---|
| NISR/WFP CFSVA household surveys (microdata) | `data/CFSVA/` | 2006, 2009, 2012, 2015, 2018, 2021, 2024 |
| CHIRPS rainfall per district (WFP/HDX) | `data/rainfall/` | 1981 – Sep 2026 |
| ERA5-Land temperature per district | `data/processed/` | 1995 – Sep 2026 |
| WFP market prices (HDX) | `data/prices/` | 2008 – Aug 2026 |
| NISR Seasonal Agricultural Survey (microdata) | `data/sas/` | 2013–2025 (full features from 2017; area, seed, fertilizer use and % sold for 2013–2016) |

## Known gaps (where to improve next)

1. **Target between surveys is interpolated** (358 of 570 target rows). Real survey values: 120 rows (CFSVA 2015–2024); FCS-based estimates: 86 rows (2006, 2009, 2012). Evaluate models on `label_source == "cari_survey"` rows.
2. **SAS 2013–2016 have no district production or fertilizer quantities** (only percentages were collected), so yields and kg/ha start in 2017; 2013 Season A cannot be placed in districts.
3. **Prices**: none before 2009; from 2017 most districts use province or national averages (`price_level`).
4. **SAS production/area totals** are blank for 2017–2019 (no survey weights in those files); yields and percentages are available.
5. Risk class thresholds (low < 15%, medium 15–30%, high ≥ 30%) are a starting choice and can be changed in `step01_target.py`.
