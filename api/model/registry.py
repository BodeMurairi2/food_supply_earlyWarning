"""Loads the saved random forest models once, and precomputes their predictions.

Nothing here retrains a model: the two pipelines saved from regression.ipynb are loaded as-is.
- evaluation model (trained 2006-2020) -> predictions for the 2021-2024 test years
- final model (trained 2006-2024)      -> forecasts for 2025-2026 and the Prediction Lab
"""

import json
from functools import cached_property

import joblib

from api import config
from api.data.dataset import LABEL_SOURCE_NAMES
from api.model.explainer import ModelExplainer
from api.model.metrics import risk_class


class ModelRegistry:
    def __init__(self, dataset):
        self.dataset = dataset
        self.spec = json.loads(config.FEATURE_SPEC_PATH.read_text())
        self.features = self.spec["features"]
        self.target = self.spec["target"]
        self.eval_model = joblib.load(config.EVAL_MODEL_PATH)
        self.final_model = joblib.load(config.FINAL_MODEL_PATH)
        self.eval_explainer = ModelExplainer(self.eval_model)
        self.final_explainer = ModelExplainer(self.final_model)

    @cached_property
    def historical(self):
        """2021-2024 rows: observed value, evaluation-model prediction, error and SHAP contributions."""
        lo, hi = config.TEST_YEARS
        df = self.dataset.df
        rows = df[df["year"].between(lo, hi)].copy()
        X = rows[self.features]
        rows["predicted"] = self.eval_model.predict(X)
        rows["observed"] = rows[self.target]
        rows["error"] = rows["predicted"] - rows["observed"]
        rows["is_real_survey"] = rows["label_source"] == "cari_survey"
        rows["observation_type"] = rows["label_source"].map(LABEL_SOURCE_NAMES)
        rows["observed_risk"] = rows["observed"].map(risk_class)
        rows["predicted_risk"] = rows["predicted"].map(risk_class)
        rows["persistence"] = rows["last_survey_food_insecure_pct"]
        shap_values = self.eval_explainer.explain(X)
        return rows, shap_values

    @cached_property
    def forecasts(self):
        """2025-2026 rows: final-model forecasts and SHAP contributions (no observed value exists)."""
        lo, hi = config.FORECAST_YEARS
        df = self.dataset.df
        rows = df[df["year"].between(lo, hi)].copy()
        X = rows[self.features]
        rows["predicted"] = self.final_model.predict(X)
        rows["predicted_risk"] = rows["predicted"].map(risk_class)
        shap_values = self.final_explainer.explain(X)
        return rows, shap_values
