# HarvestWatch: early warning for food insecurity in Rwanda

**NISR 2026 Big Data Hackathon** · Track 1: Agricultural Productivity · Team Harvest
Agnes Marie Merci Mbabazi & Bode Murai Murairi

## Problem

Rwanda measures food security well, but late. The CFSVA survey runs every three years, and price, rainfall and crop reports are published separately. In 2024, 17% of households were food insecure, from 4% in Kigali to 38% in Nyamasheke. HarvestWatch combines public NISR, satellite and market data to predict, before each survey, whether each of Rwanda's 30 districts will have **Low (<15%)**, **Medium (15–30%)** or **High (≥30%)** food insecurity, so that MINAGRI, NISR and district officers can act early.

The model predicts **one year ahead per district**. Monthly prediction was not possible: the target is only measured in survey years, and a monthly series would have required interpolating more than 90% of the data.

## Data

| Source | Use | Years |
| --- | --- | --- |
| NISR/WFP CFSVA household microdata | Target: % of households moderately or severely food insecure (WFP CARI) | 2006–2024 |
| NISR Seasonal Agricultural Survey (SAS) microdata | Yield, crop area, improved seed, fertilizer, % of harvest sold | 2013–2025 |
| CHIRPS rainfall per district (WFP, HDX) | Seasonal rainfall totals, % of normal, z-scores | 1981–2026 |
| ERA5-Land 2 m temperature (Copernicus) | Seasonal temperature and anomalies | 1995–2026 |
| WFP market prices (HDX) | Prices of beans, maize, cassava flour, Irish potato and sorghum | 2008–2026 |

The final table, `food_security_dataset.csv`, has one row per district per year (630 rows, 2006–2026). Each pipeline step is documented in [documentation/pipeline](documentation/pipeline/README.md). Raw data is not included in the repository.

## Repository structure

```
pipeline/                  data pipeline, one script per step (run_all.py runs them in order),
                           plus process_temperature.py and validate_temperature.py
download_scripts/          download ERA5-Land temperature and satellite land surface temperature from the Copernicus CDS
analysis.ipynb             feature selection, CatBoost model, experiments, TensorBoard logging
food_security_dataset.csv  final modelling table
runs/                      TensorBoard logs of the experiments
catboost_logs/             CatBoost training logs
documentation/             pipeline documentation
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## How to run

1. **Build the dataset** (needs the raw data in `data/`):
   ```bash
   python pipeline/run_all.py
   ```
2. **Train and evaluate the model:** open `analysis.ipynb`, select the `venv` kernel and run all cells.
3. **View the training logs in TensorBoard:**
   ```bash
   tensorboard --logdir runs
   ```
   Then open http://localhost:6006. TensorBoard shows the loss and macro F1 at every iteration, the 2024 test scores, each experiment's confusion matrix (Images tab) and its hyperparameters (HParams tab).

## Model

We use a **CatBoost classifier** with a multiclass loss and class weights. It suits our small tabular dataset (570 labelled rows): its symmetric trees and ordered boosting limit overfitting, and it handles the categorical `province` and `district` columns and missing values (prices start in 2008, SAS in 2013) without extra preprocessing.

**Validation:** we train on years up to 2019, validate on the 2021 survey and test on the 2024 survey (30 districts: 8 Low, 20 Medium, 2 High). Only real survey rows are used for validation and testing.

## Results (placeholder runs, 2024 survey)

These are short 50-iteration runs that prove the pipeline works end to end; the model is not tuned yet.

| Experiment | Accuracy | Macro F1 | High recall | High precision |
| --- | --- | --- | --- | --- |
| Persistence baseline (class at the last survey) | 0.700 | 0.604 | 0.50 | 0.20 |
| exp1: placeholder run, baseline features | 0.600 | 0.521 | 0.50 | 0.17 |
| exp2: + previous survey value | 0.600 | 0.528 | 0.50 | 0.14 |
| exp3: without province and district | 0.600 | 0.419 | 0.00 | 0.00 |
| exp4: previous survey value, without location | 0.667 | 0.474 | 0.00 | 0.00 |

No model beats the persistence baseline yet. Removing location makes the model miss both High districts, so it still relies on where a district is rather than on rainfall, price and harvest shocks. Next steps: train for more iterations, tune class weights so High is predicted more reliably, and forecast 2025–2026.
