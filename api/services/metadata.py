"""Reference data: provinces and districts, model and feature descriptions."""

from api import config


def locations(ctx):
    provinces = []
    for province, g in ctx.dataset.districts.groupby("province"):
        provinces.append({"province": province, "districts": sorted(g["district"])})
    return {"provinces": provinces}


def metadata(ctx):
    rf = ctx.models.final_model.named_steps["regressor"]
    lo, hi = int(ctx.dataset.df["year"].min()), int(ctx.dataset.df["year"].max())
    features = []
    for f in ctx.models.features:
        label, group, unit = config.FEATURE_INFO.get(f, (f, "Other", ""))
        features.append({"feature": f, "label": label, "group": group, "unit": unit,
                         "categorical": f in ctx.models.spec["categorical"],
                         "can_be_negative": f in config.SIGNED_FEATURES})
    return {
        "target": ctx.models.target,
        "target_label": "Households moderately or severely food insecure (%)",
        "target_scale": "0-100 (percentage of households)",
        "years": {"dataset": [lo, hi], "test": list(config.TEST_YEARS), "forecast": list(config.FORECAST_YEARS),
                  "survey_years": sorted(int(y) for y in ctx.dataset.df.loc[ctx.dataset.df["label_source"] == "cari_survey", "year"].unique())},
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
        "n_districts": int(ctx.dataset.districts.shape[0]),
    }
