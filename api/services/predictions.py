"""Prediction Lab: run the final model on a dataset row with the user's inputs."""

import numpy as np
import pandas as pd

from api import config
from api.data.dataset import LABEL_SOURCE_NAMES
from api.data.serialization import clean
from api.model.explainer import contribution_items, feature_label
from api.model.metrics import risk_class


def predict(ctx, district, year, inputs):
    """Prediction Lab: start from the dataset row for (district, year), apply the user's inputs."""
    ctx.dataset.validate_location(district=district)
    unknown = set(inputs) - set(ctx.models.features) - {"province", "district", "year"}
    if unknown:
        raise ValueError(f"Unknown features: {sorted(unknown)}")
    for f, v in inputs.items():
        if v is not None and f not in config.SIGNED_FEATURES and v < 0:
            raise ValueError(f"{feature_label(f)} cannot be negative")
    base_rows = ctx.dataset.df[(ctx.dataset.df["district"] == district) & (ctx.dataset.df["year"] == year)]
    if base_rows.empty:
        raise KeyError(f"No data row for {district} in {year}")
    row = base_rows.iloc[0].copy()
    for f, v in inputs.items():
        if f in ("province", "district", "year"):
            continue
        row[f] = np.nan if v is None else float(v)
    X = pd.DataFrame([row[ctx.models.features]])
    for f in ctx.models.spec["numeric"]:
        X[f] = pd.to_numeric(X[f], errors="coerce")
    prediction = float(ctx.models.final_model.predict(X)[0])
    contribution = ctx.models.final_explainer.explain(X).iloc[0]
    history = ctx.dataset.df[(ctx.dataset.df["district"] == district) & (ctx.dataset.df["label_source"].isin(["cari_survey", "fcs_proxy_survey"]))]
    return {
        "district": district, "province": row["province"], "year": year,
        "prediction": round(prediction, 2), "risk": risk_class(prediction),
        "base_value": round(ctx.models.final_explainer.base_value, 3),
        "contributions": contribution_items(contribution, row),
        "missing_inputs_imputed": [feature_label(f) for f in ctx.models.spec["numeric"] if pd.isna(X[f].iloc[0])],
        "history": [{"year": int(r["year"]), "observed": clean(r[ctx.models.target]),
                     "observation_type": LABEL_SOURCE_NAMES.get(r["label_source"])} for _, r in history.iterrows()],
        "dataset_value_this_year": clean(base_rows.iloc[0][ctx.models.target]),
        "model": "final (2006-2024)",
        "note": "Empty inputs are filled with the training median by the model's own pipeline.",
    }


def inputs_for(ctx, district, year):
    """Default Prediction Lab values: the dataset row for a district and year."""
    ctx.dataset.validate_location(district=district)
    r = ctx.dataset.df[(ctx.dataset.df["district"] == district) & (ctx.dataset.df["year"] == year)]
    if r.empty:
        raise KeyError(f"No data row for {district} in {year}")
    r = r.iloc[0]
    return {"district": district, "province": r["province"], "year": year,
            "inputs": {f: clean(r[f]) for f in ctx.models.spec["numeric"] if f != "year"}}
