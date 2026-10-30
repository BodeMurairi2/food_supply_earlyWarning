# HarvestWatch: early warning for food insecurity in Rwanda

**NISR 2026 Big Data Hackathon** · Track 1: Agricultural Productivity · Team Harvest
Agnes Marie Merci Mbabazi & Bode Murai Murairi

Video walkthrough: https://youtu.be/Z_OSBGWulKI

Project report: [HarvestWatch documentation (PDF)](HarvestWatch_Documentation_NISR_big_data_competition.pdf)

## Problem

Rwanda measures food security well, but late. The CFSVA survey runs every three years, and price, rainfall and crop reports are published separately. In 2024, 17% of households were food insecure, from 4% in Kigali to 38% in Nyamasheke. HarvestWatch combines public NISR, satellite and market data to predict, before each survey, the percentage of households food insecure in each of Rwanda's 30 districts. We then place each district in a risk class, **Low (<15%)**, **Medium (15–30%)** or **High (≥30%)**, so that MINAGRI, NISR and district officers can act early.

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
regression.ipynb           random forest training, evaluation and 2025–2026 forecasts
food_security_dataset.csv  final modelling table
runs/                      TensorBoard logs from our earlier CatBoost experiments
catboost_logs/             training logs from our earlier CatBoost experiments
documentation/             pipeline documentation
api/                       FastAPI backend (see below)
frontend/                  React frontend
models/                    saved random forest models
```

The backend reads top to bottom: a request goes through a router, a controller and a service.

```
api/
  main.py            creates the app, adds the routers
  config.py          paths, thresholds, feature labels, AI settings
  dependencies.py    the dataset and models shared by every request
  routers/           URLs and query parameters, one file per area
  controllers/       call the services, turn errors into HTTP responses, AI cache and rate limit
  services/          the logic behind each page
  data/              loads the dataset and boundaries, JSON helpers
  model/             loads the saved models, SHAP explanations, risk classes and scores
  agents/            AI assistant, used on every AI page: analyst.py runs the agent, parsing.py checks its answer
    instruction/     system instruction
    prompt/          user message
    tool/            web search
    memory/          session and analysis cache
  schemas/           request and response models
  assets/            district boundaries
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
2. **Train and evaluate the model:** open `regression.ipynb`, select the `venv` kernel and run all cells. The notebook saves the two models and the feature list to `models/`.
3. **Run the web app.** The app uses the saved models in `models/` and `food_security_dataset.csv`. It does not retrain anything.
   ```bash
   docker compose up --build
   ```
   Then open http://localhost:8000. To run without Docker:
   ```bash
   # backend (from the repo root), http://localhost:8000/docs
   uvicorn api.main:app --port 8000

   # frontend (second terminal), http://localhost:5173
   cd frontend
   npm install
   npm run dev
   ```
   The frontend sends `/api` requests to the backend on port 8000.

   **AI keys.** The AI Analyst and the AI assistant need an OpenRouter key (the LLM) and a Tavily key (web search). We copy `.env.example` to `.env`, fill in the keys and restart the backend. `.env` is git-ignored. `HW_LLM_MODEL` picks the model (any LiteLLM id; OpenRouter ids start with `openrouter/`), and `SEARCH_DEPTH` picks the Tavily search depth (`basic` or `advanced`). Without keys, the rest of the app still works and the AI page says which key is missing.
4. **Test the API:**
   ```bash
   python -m pytest tests -q
   ```

To put the app online with HTTPS, see [DEPLOY.md](DEPLOY.md).

## Model

We use a **random forest regressor** that predicts the percentage of households food insecure in each district and year. It suits our small tabular dataset (630 rows), and it reports how much each input moved a prediction through SHAP values.

| Setting | Value |
| --- | --- |
| Features | 45 (43 numeric; `province` and `district` are categorical) |
| Preprocessing | Median imputation for missing values, scaling, one-hot encoding |
| Forest | 500 trees, maximum depth 7, at least 2 rows per leaf, `sqrt` features per split, absolute error |

We save two models:

| Model | Trained on | Used for |
| --- | --- | --- |
| Evaluation | 2006–2020 | Testing on 2021–2024, years it never saw |
| Final | 2006–2024 | Forecasts for 2025–2026 and the Prediction Lab |

**Risk classes.** We turn each percentage into Low (below 15%), Medium (15–30%) or High (30% or more). We chose these thresholds ourselves; they are not official NISR or WFP categories.

**Testing.** The test set has 120 district-years. 2021 and 2024 are real CFSVA surveys (60 rows). 2022 and 2023 are interpolated between those surveys (60 rows). The training years 2019 and 2020 are also interpolated using the 2021 survey, so the 2021 score is slightly optimistic.

## Model performance

### Predicting the percentage

Errors are in percentage points.

| Metric | Test data 2021–2024 (120) | Real surveys 2021 & 2024 (60) | Real survey 2021 (30) | Real survey 2024 (30) |
| --- | --- | --- | --- | --- |
| MAE | 4.53 | 5.39 | 6.33 | 4.44 |
| RMSE | 5.73 | 6.77 | 7.71 | 5.68 |
| R² | 70.0% | 61.7% | 63.9% | 55.2% |

### Predicting the risk class

Precision, recall, F1 and ROC-AUC are averages across the three classes.

| Metric | Test data 2021–2024 (120) | Real surveys 2021 & 2024 (60) | Real survey 2021 (30) | Real survey 2024 (30) |
| --- | --- | --- | --- | --- |
| Accuracy | 70.0% | 66.7% | 60.0% | 73.3% |
| Precision | 72.7% | 63.1% | 74.6% | 51.7% |
| Recall | 61.9% | 55.1% | 55.4% | 51.7% |
| F1 | 64.9% | 57.4% | 58.2% | 51.7% |
| ROC-AUC | 89.2% | 84.7% | 85.6% | 87.6% |

### By class

**Test data 2021–2024** (accuracy 70.0%)

| Class | Precision | Recall | F1 | ROC-AUC | Found / actual |
| --- | --- | --- | --- | --- | --- |
| Low | 82.1% | 54.8% | 65.7% | 91.1% | 23 / 42 |
| Medium | 65.9% | 87.1% | 75.0% | 81.0% | 54 / 62 |
| High | 70.0% | 43.8% | 53.8% | 95.4% | 7 / 16 |

**Real surveys 2021 & 2024** (accuracy 66.7%)

| Class | Precision | Recall | F1 | ROC-AUC | Found / actual |
| --- | --- | --- | --- | --- | --- |
| Low | 73.3% | 55.0% | 62.9% | 87.8% | 11 / 20 |
| Medium | 65.9% | 81.8% | 73.0% | 73.8% | 27 / 33 |
| High | 50.0% | 28.6% | 36.4% | 92.5% | 2 / 7 |

**Real survey 2021** (accuracy 60.0%)

| Class | Precision | Recall | F1 | ROC-AUC | Found / actual |
| --- | --- | --- | --- | --- | --- |
| Low | 71.4% | 41.7% | 52.6% | 87.0% | 5 / 12 |
| Medium | 52.4% | 84.6% | 64.7% | 73.8% | 11 / 13 |
| High | 100.0% | 40.0% | 57.1% | 96.0% | 2 / 5 |

**Real survey 2024** (accuracy 73.3%)

| Class | Precision | Recall | F1 | ROC-AUC | Found / actual |
| --- | --- | --- | --- | --- | --- |
| Low | 75.0% | 75.0% | 75.0% | 93.2% | 6 / 8 |
| Medium | 80.0% | 80.0% | 80.0% | 80.2% | 16 / 20 |
| High | 0.0% | 0.0% | 0.0% | 89.3% | 0 / 2 |

ROC-AUC uses the share of the forest's trees that predict each class.

## Results

**Forecasts** (final model; no survey exists yet for these years):

| Year | Average | Low | Medium | High | High districts |
| --- | --- | --- | --- | --- | --- |
| 2025 | 18.9% | 7 | 22 | 1 | Ngororero (31.0%) |
| 2026 | 19.6% | 8 | 19 | 3 | Rutsiro (32.7%), Ngororero (31.8%), Nyamasheke (30.0%) |

Season A 2026 harvest data is not published yet, so the 2026 forecast uses Seasons B and C of 2025 only. Forecasts should be read as a range of about 5 to 6 points, the model's error on real surveys.

**What we found:**

- **The model's estimates are close to the recorded values.** The average error is 4.53 points on the test data and 5.39 points on real surveys.
- **It ranks districts well.** ROC-AUC for High is 92.5% on real surveys, so districts with higher estimates usually are more food insecure.
- **It places about 7 in 10 districts in the correct class.** Accuracy is 70.0% on the test data and 66.7% on real surveys.
- **It misses many High districts.** It pulls estimates toward the middle, so it found 2 of 7 High districts on real surveys and placed most of the others in Medium. It never placed a Low district in High, or a High district in Low.
- **Past food insecurity and location drive it most.** The largest contributions come from the previous survey value, the province and temperature, so the model relies heavily on where a district is and how it did before. These are associations, not proven causes.

**How to use it:** we rank districts by their estimate and start from the top, treat districts close to 30% as a warning even when they are labelled Medium, and confirm priorities with field information. With only 7 High cases on real surveys, the High figures can move a lot.
