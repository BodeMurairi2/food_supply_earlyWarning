"""Risk classes and regression scores."""

import math

import numpy as np
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error

from api import config


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
