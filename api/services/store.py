"""Loads the dataset and the saved random forest models once, and answers every data question.

Nothing here retrains a model: the two pipelines saved from regression.ipynb are loaded as-is.
- evaluation model (trained 2006-2020) -> predictions for the 2021-2024 test years
- final model (trained 2006-2024)      -> forecasts for 2025-2026 and the Prediction Lab
"""

import json
import math
from functools import cached_property

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from api import config

LABEL_SOURCE_NAMES = {
    "cari_survey": "Survey (CARI)",
    "fcs_proxy_survey": "Survey estimate (FCS)",
    "interpolated": "Interpolated",
    "backfilled": "Back-filled",
    "forecast_no_target": "No survey",
}


def clean(value):
    """JSON-safe value: NaN/inf -> None, numpy scalars -> Python numbers."""
    if isinstance(value, (np.floating, float)):
        return None if not math.isfinite(float(value)) else round(float(value), 4)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def records(df):
    return [{k: clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def risk_class(pct):
    if pct is None or (isinstance(pct, float) and math.isnan(pct)):
        return None
    for t in config.RISK_THRESHOLDS:
        if (t["min"] is None or pct >= t["min"]) and (t["max"] is None or pct < t["max"]):
            return t["label"]
    return None


def scores(y_true, y_pred):
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    if len(y_true) == 0:
        return {"n": 0, "mae": None, "rmse": None, "r2": None}
    return {
        "n": int(len(y_true)),
        "mae": round(float(mean_absolute_error(y_true, y_pred)), 3),
        "rmse": round(float(root_mean_squared_error(y_true, y_pred)), 3),
        "r2": round(float(r2_score(y_true, y_pred)), 3) if len(y_true) > 1 else None,
    }


class ModelExplainer:
    """SHAP values for one saved pipeline, summed back to the original (untransformed) features."""

    def __init__(self, pipeline):
        self.pipeline = pipeline
        self.preprocess = pipeline.named_steps["preprocess"]
        self.regressor = pipeline.named_steps["regressor"]
        self.explainer = shap.TreeExplainer(self.regressor)
        self.base_value = float(np.ravel(self.explainer.expected_value)[0])
        self.original_names = [self._original(n) for n in self.preprocess.get_feature_names_out()]

    @staticmethod
    def _original(name):
        name = name.split("__", 1)[1]
        for categorical in ("district", "province"):
            if name.startswith(categorical + "_"):
                return categorical
        return name

    def explain(self, X):
        """DataFrame (rows x original features) of SHAP contributions in percentage points."""
        Xt = self.preprocess.transform(X)
        Xt = Xt.toarray() if hasattr(Xt, "toarray") else Xt
        values = self.explainer.shap_values(Xt)
        return pd.DataFrame(values, columns=self.original_names, index=X.index).T.groupby(level=0).sum().T


class Store:
    def __init__(self):
        self.spec = json.loads(config.FEATURE_SPEC_PATH.read_text())
        self.features = self.spec["features"]
        self.target = self.spec["target"]
        # The notebook replaces the one infinite value (a yield change after a zero yield) with NaN.
        self.df = pd.read_csv(config.DATASET_PATH).replace([np.inf, -np.inf], np.nan)
        self.eval_model = joblib.load(config.EVAL_MODEL_PATH)
        self.final_model = joblib.load(config.FINAL_MODEL_PATH)
        self.eval_explainer = ModelExplainer(self.eval_model)
        self.final_explainer = ModelExplainer(self.final_model)
        self.boundaries = json.loads(config.BOUNDARIES_PATH.read_text())
        self.districts = (self.df[["province", "district"]].drop_duplicates()
                          .sort_values(["province", "district"]).reset_index(drop=True))

    # ---------- helpers ----------
    def feature_label(self, feature):
        return config.FEATURE_INFO.get(feature, (feature, "Other", ""))[0]

    def contributions(self, shap_row, values_row, top=None):
        items = []
        for feature, contribution in shap_row.items():
            label, group, unit = config.FEATURE_INFO.get(feature, (feature, "Other", ""))
            value = values_row.get(feature)
            items.append({"feature": feature, "label": label, "group": group, "unit": unit,
                          "value": clean(value), "contribution": round(float(contribution), 3)})
        items.sort(key=lambda d: abs(d["contribution"]), reverse=True)
        return items[:top] if top else items

    def filter_locations(self, df, province=None, district=None):
        if province:
            df = df[df["province"] == province]
        if district:
            df = df[df["district"] == district]
        return df

    def validate_location(self, province=None, district=None):
        if province and province not in set(self.districts["province"]):
            raise KeyError(f"Unknown province: {province}")
        if district and district not in set(self.districts["district"]):
            raise KeyError(f"Unknown district: {district}")
        if province and district:
            match = self.districts[self.districts["district"] == district]["province"].iloc[0]
            if match != province:
                raise KeyError(f"{district} is in {match}, not {province}")

    # ---------- precomputed tables ----------
    @cached_property
    def historical(self):
        """2021-2024 rows: observed value, evaluation-model prediction, error and SHAP contributions."""
        lo, hi = config.TEST_YEARS
        rows = self.df[self.df["year"].between(lo, hi)].copy()
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
        rows = self.df[self.df["year"].between(lo, hi)].copy()
        X = rows[self.features]
        rows["predicted"] = self.final_model.predict(X)
        rows["predicted_risk"] = rows["predicted"].map(risk_class)
        shap_values = self.final_explainer.explain(X)
        return rows, shap_values

    # ---------- endpoints ----------
    def locations(self):
        provinces = []
        for province, g in self.districts.groupby("province"):
            provinces.append({"province": province, "districts": sorted(g["district"])})
        return {"provinces": provinces}

    def metadata(self):
        rf = self.final_model.named_steps["regressor"]
        lo, hi = int(self.df["year"].min()), int(self.df["year"].max())
        features = []
        for f in self.features:
            label, group, unit = config.FEATURE_INFO.get(f, (f, "Other", ""))
            features.append({"feature": f, "label": label, "group": group, "unit": unit,
                             "categorical": f in self.spec["categorical"],
                             "can_be_negative": f in config.SIGNED_FEATURES})
        return {
            "target": self.target,
            "target_label": "Households moderately or severely food insecure (%)",
            "target_scale": "0-100 (percentage of households)",
            "years": {"dataset": [lo, hi], "test": list(config.TEST_YEARS), "forecast": list(config.FORECAST_YEARS),
                      "survey_years": sorted(int(y) for y in self.df.loc[self.df["label_source"] == "cari_survey", "year"].unique())},
            "risk_thresholds": config.RISK_THRESHOLDS,
            "risk_thresholds_note": config.THRESHOLDS_NOTE,
            "model": {
                "type": "RandomForestRegressor (scikit-learn pipeline: median imputation, scaling, one-hot encoding)",
                "n_estimators": rf.n_estimators, "max_depth": rf.max_depth,
                "evaluation_model_training_years": "2006-2020",
                "final_model_training_years": "2006-2024",
            },
            "features": features,
            "key_features": config.KEY_FEATURES,
            "n_districts": int(self.districts.shape[0]),
        }

    def value_for_year(self, year):
        """Per-district value for a year: observed/estimated up to 2024, forecast for 2025-2026."""
        if year in range(config.FORECAST_YEARS[0], config.FORECAST_YEARS[1] + 1):
            rows, _ = self.forecasts
            rows = rows[rows["year"] == year]
            out = rows[["province", "district"]].copy()
            out["value"] = rows["predicted"].values
            out["value_type"] = "Forecast"
        else:
            rows = self.df[self.df["year"] == year]
            out = rows[["province", "district"]].copy()
            out["value"] = rows[self.target].values
            out["value_type"] = rows["label_source"].map(LABEL_SOURCE_NAMES).values
        out["risk"] = out["value"].map(risk_class)
        return out

    def overview(self, province=None, district=None, year=2025):
        self.validate_location(province, district)
        values = self.value_for_year(year)
        selected = self.filter_locations(values, province, district)
        counts = {t["label"]: int((selected["risk"] == t["label"]).sum()) for t in config.RISK_THRESHOLDS}

        latest = self.filter_locations(self.df[self.df["label_source"] == "cari_survey"], province, district)
        latest_year = int(latest["year"].max())
        latest_avg = latest.loc[latest["year"] == latest_year, self.target].mean()

        fc_rows, _ = self.forecasts
        fc_rows = self.filter_locations(fc_rows, province, district)
        forecast_avg = {str(int(y)): clean(g["predicted"].mean()) for y, g in fc_rows.groupby("year")}

        # Yearly trend (simple average over the selected districts)
        base = self.filter_locations(self.df, province, district)
        trend = []
        for y, g in base.groupby("year"):
            y = int(y)
            if y >= config.FORECAST_YEARS[0]:
                fi = fc_rows[fc_rows["year"] == y]["predicted"].mean()
                kind = "Forecast"
            else:
                fi = g[self.target].mean()
                kind = "Survey" if (g["label_source"] == "cari_survey").any() else (
                    "Survey estimate" if (g["label_source"] == "fcs_proxy_survey").any() else "Interpolated")
            trend.append({"year": y, "food_insecure_pct": clean(fi), "value_type": kind,
                          "rain_pct_normal": clean(g["rain_12m_pct_normal"].mean()),
                          "temp_anomaly_c": clean(g["temp_12m_anomaly_c"].mean()),
                          "maize_yield_kg_ha": clean(g["sas_maize_yield_kg_ha"].mean()),
                          "beans_yield_kg_ha": clean(g["sas_beans_yield_kg_ha"].mean())})

        top = selected.sort_values("value", ascending=False).head(10)
        return {
            "filters": {"province": province, "district": district, "year": year},
            "n_districts": int(selected.shape[0]),
            "latest_survey": {"year": latest_year, "avg_food_insecure_pct": clean(latest_avg)},
            "forecast_avg": forecast_avg,
            "selected_year": {"year": year, "value_type": "Forecast" if year >= config.FORECAST_YEARS[0] else "Observed or estimated",
                              "avg_food_insecure_pct": clean(selected["value"].mean()), "risk_counts": counts},
            "map": records(values.assign(selected=values["district"].isin(selected["district"]))),
            "trend": trend,
            "top_districts": records(top),
            "note": "Province and national figures are simple averages of district values.",
        }

    def historical_table(self, province=None, district=None, year=None):
        self.validate_location(province, district)
        rows, _ = self.historical
        rows = self.filter_locations(rows, province, district)
        if year:
            rows = rows[rows["year"] == year]
        cols = ["year", "province", "district", "observed", "observation_type", "is_real_survey", "predicted",
                "error", "observed_risk", "predicted_risk", "persistence"]
        rows = rows.sort_values(["year", "province", "district"])
        survey = rows[rows["is_real_survey"]]
        return {
            "rows": records(rows[cols]),
            "metrics": {
                "all_rows": scores(rows["observed"], rows["predicted"]),
                "real_surveys": scores(survey["observed"], survey["predicted"]),
                "persistence_real_surveys": scores(survey["observed"], survey["persistence"]),
            },
        }

    def performance(self):
        rows, _ = self.historical
        survey = rows[rows["is_real_survey"]]
        train = self.df[self.df["year"] < config.TEST_YEARS[0]]
        by_year = [{"year": int(y), "observation_type": g["observation_type"].iloc[0], **scores(g["observed"], g["predicted"])}
                   for y, g in rows.groupby("year")]
        by_province = [{"province": p, **scores(g["observed"], g["predicted"])} for p, g in survey.groupby("province")]
        class_agreement = (survey["observed_risk"] == survey["predicted_risk"]).mean()
        return {
            "evaluation_setup": "Model trained on 2006-2020, tested on 2021-2024. 2021 and 2024 are real CFSVA surveys; "
                                "2022-2023 are interpolated between them.",
            "train": scores(train[self.target], self.eval_model.predict(train[self.features])),
            "test_all_rows": scores(rows["observed"], rows["predicted"]),
            "test_real_surveys": scores(survey["observed"], survey["predicted"]),
            "persistence_real_surveys": scores(survey["observed"], survey["persistence"]),
            "risk_class_agreement_real_surveys": clean(class_agreement),
            "by_year": by_year,
            "by_province_real_surveys": by_province,
            "caveats": [
                "Training years 2019-2020 are interpolated using the 2021 survey, so the 2021 score is slightly optimistic.",
                "The test set contains 60 real survey values (30 districts x 2 rounds).",
            ],
        }

    def feature_importance(self, model="final"):
        pipeline, explainer = (self.final_model, self.final_explainer) if model == "final" else (self.eval_model, self.eval_explainer)
        rf = pipeline.named_steps["regressor"]
        impurity = pd.Series(rf.feature_importances_, index=explainer.original_names).groupby(level=0).sum()
        _, shap_values = self.forecasts if model == "final" else self.historical
        mean_abs = shap_values.abs().mean()
        items = []
        for f in impurity.index:
            label, group, unit = config.FEATURE_INFO.get(f, (f, "Other", ""))
            items.append({"feature": f, "label": label, "group": group,
                          "impurity_importance": round(float(impurity[f]), 4),
                          "mean_abs_shap": round(float(mean_abs.get(f, 0.0)), 3)})
        items.sort(key=lambda d: d["mean_abs_shap"], reverse=True)
        return {
            "model": "final (2006-2024)" if model == "final" else "evaluation (2006-2020)",
            "shap_rows": "2025-2026 forecast rows" if model == "final" else "2021-2024 test rows",
            "note": "Importance shows how much a feature moves the model's predictions, not a causal effect.",
            "features": items,
        }

    def explain(self, district, year):
        self.validate_location(district=district)
        if config.TEST_YEARS[0] <= year <= config.TEST_YEARS[1]:
            rows, shap_values = self.historical
            model_name = "evaluation (2006-2020)"
            base = self.eval_explainer.base_value
        elif config.FORECAST_YEARS[0] <= year <= config.FORECAST_YEARS[1]:
            rows, shap_values = self.forecasts
            model_name = "final (2006-2024)"
            base = self.final_explainer.base_value
        else:
            raise KeyError("Explanations are available for 2021-2026")
        mask = (rows["district"] == district) & (rows["year"] == year)
        row = rows[mask].iloc[0]
        contribution = shap_values[mask].iloc[0]
        return {
            "district": district, "province": row["province"], "year": year, "model": model_name,
            "prediction": clean(row["predicted"]), "risk": risk_class(row["predicted"]),
            "observed": clean(row.get("observed")) if "observed" in rows else None,
            "base_value": round(base, 3),
            "contributions": self.contributions(contribution, row),
            "note": "Contributions (SHAP) show how each input moved this prediction away from the average prediction. "
                    "They describe the model, not causes.",
        }

    def forecast_table(self, province=None, district=None, top_drivers=3):
        self.validate_location(province, district)
        rows, shap_values = self.forecasts
        observed_2024 = self.df[self.df["year"] == 2024].set_index("district")[self.target]
        out = []
        for d, g in self.filter_locations(rows, province, district).groupby("district"):
            entry = {"province": g["province"].iloc[0], "district": d, "observed_2024": clean(observed_2024.get(d))}
            for _, r in g.iterrows():
                y = int(r["year"])
                drivers = self.contributions(shap_values.loc[r.name], r, top=top_drivers)
                entry[f"predicted_{y}"] = clean(r["predicted"])
                entry[f"risk_{y}"] = risk_class(r["predicted"])
                entry[f"drivers_{y}"] = [{"label": x["label"], "contribution": x["contribution"]} for x in drivers]
            out.append(entry)
        return {
            "rows": out,
            "status": {
                "2025": "Complete inputs: rainfall, temperature and prices to March 2025; harvests B/C 2024 and A 2025.",
                "2026": "Season A 2026 harvest data (SAS) is not published yet; agriculture inputs use Seasons B and C 2025 only.",
            },
            "note": "No CFSVA survey exists for 2025 or 2026, so there are no observed values to compare with. "
                    "Forecasts come from the final model (trained 2006-2024). Typical error on real surveys: about 5-6 points.",
        }

    def district_series(self, district):
        self.validate_location(district=district)
        d = self.df[self.df["district"] == district].sort_values("year")
        hist, _ = self.historical
        fc, _ = self.forecasts
        test_pred = hist[hist["district"] == district].set_index("year")["predicted"]
        fc_pred = fc[fc["district"] == district].set_index("year")["predicted"]
        series = []
        for _, r in d.iterrows():
            y = int(r["year"])
            series.append({"year": y,
                           "observed": clean(r[self.target]),
                           "observation_type": LABEL_SOURCE_NAMES.get(r["label_source"]),
                           "test_prediction": clean(test_pred.get(y)),
                           "forecast": clean(fc_pred.get(y))})
        return {"district": district, "province": d["province"].iloc[0], "series": series}

    def predict(self, district, year, inputs):
        """Prediction Lab: start from the dataset row for (district, year), apply the user's inputs."""
        self.validate_location(district=district)
        unknown = set(inputs) - set(self.features) - {"province", "district", "year"}
        if unknown:
            raise ValueError(f"Unknown features: {sorted(unknown)}")
        for f, v in inputs.items():
            if v is not None and f not in config.SIGNED_FEATURES and v < 0:
                raise ValueError(f"{self.feature_label(f)} cannot be negative")
        base_rows = self.df[(self.df["district"] == district) & (self.df["year"] == year)]
        if base_rows.empty:
            raise KeyError(f"No data row for {district} in {year}")
        row = base_rows.iloc[0].copy()
        for f, v in inputs.items():
            if f in ("province", "district", "year"):
                continue
            row[f] = np.nan if v is None else float(v)
        X = pd.DataFrame([row[self.features]])
        for f in self.spec["numeric"]:
            X[f] = pd.to_numeric(X[f], errors="coerce")
        prediction = float(self.final_model.predict(X)[0])
        contribution = self.final_explainer.explain(X).iloc[0]
        history = self.df[(self.df["district"] == district) & (self.df["label_source"].isin(["cari_survey", "fcs_proxy_survey"]))]
        return {
            "district": district, "province": row["province"], "year": year,
            "prediction": round(prediction, 2), "risk": risk_class(prediction),
            "base_value": round(self.final_explainer.base_value, 3),
            "contributions": self.contributions(contribution, row),
            "missing_inputs_imputed": [self.feature_label(f) for f in self.spec["numeric"] if pd.isna(X[f].iloc[0])],
            "history": [{"year": int(r["year"]), "observed": clean(r[self.target]),
                         "observation_type": LABEL_SOURCE_NAMES.get(r["label_source"])} for _, r in history.iterrows()],
            "dataset_value_this_year": clean(base_rows.iloc[0][self.target]),
            "model": "final (2006-2024)",
            "note": "Empty inputs are filled with the training median by the model's own pipeline.",
        }

    def inputs_for(self, district, year):
        """Default Prediction Lab values: the dataset row for a district and year."""
        self.validate_location(district=district)
        r = self.df[(self.df["district"] == district) & (self.df["year"] == year)]
        if r.empty:
            raise KeyError(f"No data row for {district} in {year}")
        r = r.iloc[0]
        return {"district": district, "province": r["province"], "year": year,
                "inputs": {f: clean(r[f]) for f in self.spec["numeric"] if f != "year"}}

    # ---------- visualizations ----------
    def _viz_info(self, variable):
        if variable not in config.VIZ_VARIABLES:
            raise ValueError(f"Unknown variable: {variable}")
        label, topic, unit, aggregation, change = config.VIZ_VARIABLES[variable]
        return {"key": variable, "label": label, "topic": topic, "unit": unit,
                "aggregation": aggregation, "change": change}

    @staticmethod
    def _combine(df, column, aggregation, by):
        """Yearly value per group: sum for production, simple average otherwise. All-missing stays missing."""
        g = df.groupby(by)[column]
        return g.sum(min_count=1) if aggregation == "sum" else g.mean()

    def _partial_years(self, variable):
        return config.SAS_PARTIAL_YEARS if variable.startswith("sas_") else {}

    def viz_variables(self):
        items = []
        for key in config.VIZ_VARIABLES:
            info = self._viz_info(key)
            years = self.df.loc[self.df[key].notna(), "year"].unique()
            info["years"] = sorted(int(y) for y in years)
            info["partial_years"] = sorted(self._partial_years(key))
            items.append(info)
        return {
            "variables": items,
            "topics": list(dict.fromkeys(v["topic"] for v in items)),
            "years": [int(self.df["year"].min()), int(self.df["year"].max())],
            "default_years": [config.TEST_YEARS[0], config.FORECAST_YEARS[1]],
            "note": "Each year covers April of the year before to March of that year (the 12 months before the "
                    "April-May CFSVA survey). Harvests in year t are Seasons B and C of t-1 and Season A of t.",
        }

    def viz_trends(self, variable, level="province", province=None, district=None, start_year=2021, end_year=2026):
        info = self._viz_info(variable)
        if start_year > end_year:
            raise ValueError("Start year must not be after end year")
        self.validate_location(province, district)
        agg = info["aggregation"]
        d = self.df[self.df["year"].between(start_year, end_year)]
        partial = {y: n for y, n in self._partial_years(variable).items() if start_year <= y <= end_year}

        national = self._combine(d, variable, agg, "year")
        if level == "province":
            groups, by = d, "province"
        else:
            groups, by = self.filter_locations(d, province), "district"
        values = self._combine(groups, variable, agg, [by, "year"])
        owner = groups.drop_duplicates(by).set_index(by, drop=False)["province"]

        series = []
        for name in sorted(values.index.get_level_values(0).unique()):
            s = values.loc[name]
            series.append({"name": name, "province": owner[name],
                           "points": [{"year": int(y), "value": clean(v)} for y, v in s.items()]})

        # Ranking over complete years only, so a partial harvest year does not look like a collapse.
        complete = [int(y) for y, v in national.items() if pd.notna(v) and int(y) not in partial]
        comparison = []
        if complete:
            first, last = complete[0], complete[-1]
            for s in series:
                pts = {p["year"]: p["value"] for p in s["points"]}
                vals = [pts[y] for y in complete if pts.get(y) is not None]
                a, b = pts.get(first), pts.get(last)
                if a is None or b is None or first == last:
                    change = None
                elif info["change"] == "pct":
                    change = clean((b - a) / a * 100) if a else None
                else:
                    change = clean(b - a)
                comparison.append({"name": s["name"], "province": s["province"],
                                   "mean": clean(np.mean(vals)) if vals else None,
                                   "start": a, "end": b, "change": change})

        notes = []
        if agg == "sum":
            notes.append("Province and national values are sums of district totals.")
        else:
            notes.append("Province and national values are simple averages of district values.")
        notes += list(partial.values())
        missing = int(d[variable].isna().sum())
        if missing:
            notes.append(f"{missing} of {len(d)} district-years in this range have no value for this variable.")
        if not complete:
            notes.append("No data for this variable in the selected years.")

        return {
            "variable": info,
            "level": level,
            "filters": {"province": province, "district": district, "start_year": start_year, "end_year": end_year},
            "highlight": district if level == "district" else province,
            "years": list(range(start_year, end_year + 1)),
            "series": series,
            "national": [{"year": int(y), "value": clean(v)} for y, v in national.items()],
            "comparison": {"from_year": complete[0] if complete else None,
                           "to_year": complete[-1] if complete else None,
                           "change_kind": info["change"], "rows": comparison},
            "partial_years": sorted(partial),
            "notes": notes,
        }

    def viz_profile(self, province=None, district=None, start_year=2021, end_year=2026):
        """Rain, temperature and staple production for one area, each kept in its own units."""
        if start_year > end_year:
            raise ValueError("Start year must not be after end year")
        self.validate_location(province, district)
        d = self.filter_locations(self.df[self.df["year"].between(start_year, end_year)], province, district)
        area = district or province or "Rwanda"
        rows = []
        for y, g in d.groupby("year"):
            row = {"year": int(y),
                   "rain_12m_mm": clean(g["rain_12m_mm"].mean()),
                   "rain_12m_pct_normal": clean(g["rain_12m_pct_normal"].mean()),
                   "temp_12m_c": clean(g["temp_12m_c"].mean()),
                   "temp_12m_anomaly_c": clean(g["temp_12m_anomaly_c"].mean())}
            for c in config.STAPLE_CROPS:
                row[f"{c}_production_t"] = clean(g[f"sas_{c}_production_t"].sum(min_count=1))
            rows.append(row)
        return {
            "area": area,
            "level": "district" if district else "province" if province else "national",
            "crops": [{"key": f"{c}_production_t", "label": config.VIZ_VARIABLES[f"sas_{c}_production_t"][0]}
                      for c in config.STAPLE_CROPS],
            "rows": rows,
            "partial_years": sorted(y for y in config.SAS_PARTIAL_YEARS if start_year <= y <= end_year),
            "notes": ["Rainfall and temperature are averages over the area's districts; production is the sum.",
                      *[n for y, n in config.SAS_PARTIAL_YEARS.items() if start_year <= y <= end_year]],
        }

    # ---------- AI Analyst ----------
    def ai_context(self, district, year):
        """Everything the AI Analyst may use about one district-year, straight from the model and dataset."""
        e = self.explain(district, year)
        series = self.district_series(district)["series"]
        d = self.df[self.df["district"] == district].set_index("year")
        recent = []
        for y in range(max(2006, year - 3), year + 1):
            if y not in d.index:
                continue
            r = d.loc[y]
            recent.append({"year": y,
                           "rain_pct_of_normal": clean(r["rain_12m_pct_normal"]),
                           "dry_months": clean(r["rain_n_dry_months"]),
                           "temp_anomaly_c": clean(r["temp_12m_anomaly_c"]),
                           **{f"{c}_yield_kg_ha": clean(r[f"sas_{c}_yield_kg_ha"]) for c in config.STAPLE_CROPS},
                           "beans_price_rwf_kg": clean(r["price_beans_rwf_kg"]),
                           "maize_price_rwf_kg": clean(r["price_maize_rwf_kg"])})
        fc, _ = self.forecasts
        fc = fc[fc["district"] == district].set_index("year")["predicted"]
        return {
            "district": district, "province": e["province"], "year": year,
            "model": {"name": f"Random forest, {e['model']}",
                      "target": "share of households moderately or severely food insecure (CARI), %",
                      "prediction_pct": round(e["prediction"], 1), "risk_class": e["risk"],
                      "risk_thresholds": "Low < 15%, Medium 15-30%, High >= 30% (illustrative, not official NISR categories)",
                      "observed_pct_this_year": e["observed"], "model_average_pct": round(e["base_value"], 1),
                      "typical_error_points": "MAE 5.4 on 2021/2024 real surveys",
                      "forecasts": {str(int(y)): round(float(v), 1) for y, v in fc.items()}},
            "contributions": [{"feature": c["label"], "value": c["value"], "unit": c["unit"],
                               "points": round(c["contribution"], 2)} for c in e["contributions"][:8]],
            "survey_history": [{"year": p["year"], "pct": p["observed"], "type": p["observation_type"]}
                               for p in series if p["observation_type"] in ("Survey (CARI)", "Survey estimate (FCS)")],
            "recent_inputs": recent,
            "data_notes": [e["note"],
                           "Each year covers April of the year before to March of that year.",
                           *([config.SAS_PARTIAL_YEARS[year]] if year in config.SAS_PARTIAL_YEARS else [])],
        }
