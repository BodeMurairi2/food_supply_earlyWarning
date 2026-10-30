"""Settings for the HarvestWatch API: file locations, risk thresholds and feature labels."""

import os
from pathlib import Path

from dotenv import load_dotenv

# API keys live in .env at the repo root (see .env.example); they are never sent to the frontend.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

ROOT = Path(__file__).resolve().parent.parent
DATASET_PATH = Path(os.getenv("HW_DATASET_PATH", ROOT / "food_security_dataset.csv"))
MODELS_DIR = Path(os.getenv("HW_MODELS_DIR", ROOT / "models"))
EVAL_MODEL_PATH = MODELS_DIR / "rf_eval_2006_2020.joblib"      # trained 2006-2020, evaluated on 2021-2024
FINAL_MODEL_PATH = MODELS_DIR / "rf_final_2006_2024.joblib"    # trained 2006-2024, used for 2025-2026 forecasts
FEATURE_SPEC_PATH = MODELS_DIR / "feature_spec.json"
BOUNDARIES_PATH = Path(__file__).resolve().parent / "assets" / "rwanda_districts.geojson"

CORS_ORIGINS = os.getenv("HW_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

# Illustrative risk thresholds (% of households food insecure), defined in pipeline/step01_target.py.
# They are a project choice, not official NISR categories, and can be changed here.
RISK_THRESHOLDS = [
    {"label": "Low", "min": None, "max": 15.0},
    {"label": "Medium", "min": 15.0, "max": 30.0},
    {"label": "High", "min": 30.0, "max": None},
]
THRESHOLDS_NOTE = "Illustrative, configurable thresholds chosen by the project team; not official NISR categories."

TEST_YEARS = (2021, 2024)        # years the evaluation model never saw
FORECAST_YEARS = (2025, 2026)    # no CFSVA survey yet for these years

# Human-readable labels, groups and units for every model feature (used by the frontend).
FEATURE_INFO = {
    "year": ("Year", "Time", ""),
    "province": ("Province", "Location", ""),
    "district": ("District", "Location", ""),
    "last_survey_food_insecure_pct": ("Food insecurity at previous survey", "History", "%"),
    "rain_12m_mm": ("Rainfall, 12 months", "Climate", "mm"),
    "rain_n_dry_months": ("Dry months (<60% of normal)", "Climate", "months"),
    "rain_n_wet_months": ("Very wet months (>150% of normal)", "Climate", "months"),
    "rain_seasonB_mm": ("Season B rainfall (Mar–May)", "Climate", "mm"),
    "rain_seasonA_mm": ("Season A rainfall (Sep–Dec)", "Climate", "mm"),
    "temp_12m_c": ("Mean temperature, 12 months", "Climate", "°C"),
    "temp_max_month_c": ("Warmest month temperature", "Climate", "°C"),
    "temp_seasonB_c": ("Season B temperature", "Climate", "°C"),
    "temp_seasonA_c": ("Season A temperature", "Climate", "°C"),
    "sas_maize_yield_kg_ha": ("Maize yield", "Agriculture", "kg/ha"),
    "sas_maize_area_ha": ("Maize area", "Agriculture", "ha"),
    "sas_beans_yield_kg_ha": ("Beans yield", "Agriculture", "kg/ha"),
    "sas_beans_area_ha": ("Beans area", "Agriculture", "ha"),
    "sas_cassava_yield_kg_ha": ("Cassava yield", "Agriculture", "kg/ha"),
    "sas_cassava_area_ha": ("Cassava area", "Agriculture", "ha"),
    "sas_irish_potato_yield_kg_ha": ("Irish potato yield", "Agriculture", "kg/ha"),
    "sas_irish_potato_area_ha": ("Irish potato area", "Agriculture", "ha"),
    "sas_sweet_potato_yield_kg_ha": ("Sweet potato yield", "Agriculture", "kg/ha"),
    "sas_sweet_potato_area_ha": ("Sweet potato area", "Agriculture", "ha"),
    "sas_sorghum_yield_kg_ha": ("Sorghum yield", "Agriculture", "kg/ha"),
    "sas_sorghum_area_ha": ("Sorghum area", "Agriculture", "ha"),
    "sas_banana_yield_kg_ha": ("Banana yield", "Agriculture", "kg/ha"),
    "sas_banana_area_ha": ("Banana area", "Agriculture", "ha"),
    "sas_rice_yield_kg_ha": ("Rice yield", "Agriculture", "kg/ha"),
    "sas_rice_area_ha": ("Rice area", "Agriculture", "ha"),
    "sas_improved_seed_pct": ("Plots with improved seed", "Agriculture", "%"),
    "sas_sold_pct": ("Share of harvest sold", "Agriculture", "%"),
    "sas_inorganic_fert_plots_pct": ("Plots with inorganic fertilizer", "Agriculture", "%"),
    "sas_inorganic_kg_ha": ("Inorganic fertilizer", "Agriculture", "kg/ha"),
    "sas_dap_kg_ha": ("DAP fertilizer", "Agriculture", "kg/ha"),
    "sas_urea_kg_ha": ("Urea fertilizer", "Agriculture", "kg/ha"),
    "sas_npk_kg_ha": ("NPK fertilizer", "Agriculture", "kg/ha"),
    "sas_maize_yield_change_pct": ("Maize yield change vs previous year", "Agriculture", "%"),
    "sas_beans_yield_change_pct": ("Beans yield change vs previous year", "Agriculture", "%"),
    "sas_cassava_yield_change_pct": ("Cassava yield change vs previous year", "Agriculture", "%"),
    "sas_irish_potato_yield_change_pct": ("Irish potato yield change vs previous year", "Agriculture", "%"),
    "price_beans_rwf_kg": ("Beans price", "Markets", "RWF/kg"),
    "price_maize_rwf_kg": ("Maize price", "Markets", "RWF/kg"),
    "price_cassava_flour_rwf_kg": ("Cassava flour price", "Markets", "RWF/kg"),
    "price_irish_potato_rwf_kg": ("Irish potato price", "Markets", "RWF/kg"),
    "price_sorghum_rwf_kg": ("Sorghum price", "Markets", "RWF/kg"),
}
# Features whose values can be negative (changes); all other numeric features must be >= 0.
SIGNED_FEATURES = {f for f in FEATURE_INFO if f.endswith("_change_pct")}
# Shown first in the Prediction Lab; the rest go under "More inputs".
KEY_FEATURES = [
    "last_survey_food_insecure_pct",
    "rain_12m_mm", "rain_seasonA_mm", "rain_seasonB_mm", "rain_n_dry_months", "rain_n_wet_months",
    "temp_12m_c", "temp_max_month_c",
    "sas_maize_yield_kg_ha", "sas_beans_yield_kg_ha", "sas_cassava_yield_kg_ha", "sas_irish_potato_yield_kg_ha",
    "sas_improved_seed_pct", "sas_inorganic_fert_plots_pct", "sas_sold_pct",
    "price_beans_rwf_kg", "price_maize_rwf_kg", "price_cassava_flour_rwf_kg",
    "price_irish_potato_rwf_kg", "price_sorghum_rwf_kg",
]

# Variables on the Visualizations page: (label, topic, unit, how districts combine, how change is shown).
# Sums are used for production (tonnes add up); averages for everything else.
# "pct" change only makes sense for quantities with a true zero; temperatures and anomalies use differences.
STAPLE_CROPS = ["maize", "beans", "cassava", "irish_potato", "sorghum"]
_CROP_NAMES = {"maize": "Maize", "beans": "Beans", "cassava": "Cassava", "irish_potato": "Irish potato",
               "sweet_potato": "Sweet potato", "sorghum": "Sorghum", "banana": "Banana", "rice": "Rice"}
VIZ_VARIABLES = {
    "rain_12m_mm": ("Rainfall, 12 months", "Rainfall", "mm", "mean", "pct"),
    "rain_seasonA_mm": ("Season A rainfall (Sep–Dec)", "Rainfall", "mm", "mean", "pct"),
    "rain_seasonB_mm": ("Season B rainfall (Mar–May)", "Rainfall", "mm", "mean", "pct"),
    "rain_12m_pct_normal": ("Rainfall, % of long-term normal", "Rainfall", "%", "mean", "diff"),
    "rain_n_dry_months": ("Dry months (<60% of normal)", "Rainfall", "months", "mean", "diff"),
    "temp_12m_c": ("Mean temperature, 12 months", "Temperature", "°C", "mean", "diff"),
    "temp_max_month_c": ("Warmest month temperature", "Temperature", "°C", "mean", "diff"),
    "temp_seasonA_c": ("Season A temperature", "Temperature", "°C", "mean", "diff"),
    "temp_seasonB_c": ("Season B temperature", "Temperature", "°C", "mean", "diff"),
    "temp_12m_anomaly_c": ("Temperature anomaly, 12 months", "Temperature", "°C", "mean", "diff"),
    **{f"sas_{c}_production_t": (f"{n} production", "Production", "t", "sum", "pct") for c, n in _CROP_NAMES.items()},
    **{f"sas_{c}_yield_kg_ha": (f"{n} yield", "Yield", "kg/ha", "mean", "pct") for c, n in _CROP_NAMES.items()},
    **{f"price_{c}_rwf_kg": (f"{n} price", "Prices", "RWF/kg", "mean", "pct")
       for c, n in [("beans", "Beans"), ("maize", "Maize"), ("cassava_flour", "Cassava flour"),
                    ("irish_potato", "Irish potato"), ("sorghum", "Sorghum")]},
}
# Harvest data for the latest year is incomplete (Season A not yet published).
SAS_PARTIAL_YEARS = {2026: "2026 covers Seasons B and C of 2025 only; Season A 2026 is not published yet, so totals are incomplete."}

# ---------- AI Analyst ----------
# The LLM is reached through LiteLLM; an "openrouter/..." model uses OPENROUTER_API_KEY.
LLM_MODEL = os.getenv("HW_LLM_MODEL", "openrouter/anthropic/claude-sonnet-5.5")
TAVILY_URL = "https://api.tavily.com/search"
# Tavily search depth: "basic" (cheaper) or "advanced" (better results, more credits); also "fast", "ultra-fast".
SEARCH_DEPTH = os.getenv("SEARCH_DEPTH", "basic").strip().lower()
if SEARCH_DEPTH not in {"basic", "advanced", "fast", "ultra-fast"}:
    SEARCH_DEPTH = "basic"
AI_MAX_SEARCHES = 4          # web searches the agent may run per analysis
AI_RESULTS_PER_SEARCH = 5
AI_TIMEOUT_S = 240           # whole analysis, including searches
AI_ASSISTANT_MAX_TOKENS = 12000   # long answers on the Prediction Lab, Forecasts and Visualizations pages
AI_ASSISTANT_MAX_SOURCES = 6
# Limits for the public demo (cached answers do not count).
AI_LIMIT_PER_CLIENT_HOUR = int(os.getenv("HW_AI_LIMIT_PER_HOUR", "5"))
AI_LIMIT_PER_DAY = int(os.getenv("HW_AI_LIMIT_PER_DAY", "60"))

# Built React app (npm run build); served by FastAPI when present, so the whole app is one service.
FRONTEND_DIST = Path(os.getenv("HW_FRONTEND_DIST", ROOT / "frontend" / "dist"))


def ai_status():
    """Which AI services are configured (never the keys themselves)."""
    return {"llm": bool(os.getenv("OPENROUTER_API_KEY")) or not LLM_MODEL.startswith("openrouter/"),
            "search": bool(os.getenv("TAVILY_API_KEY")),
            "model": LLM_MODEL}
