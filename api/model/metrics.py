"""Risk classes and regression scores."""

import math

import numpy as np
from sklearn.metrics import (accuracy_score, mean_absolute_error, precision_recall_fscore_support, r2_score, roc_auc_score,
                             root_mean_squared_error)

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


def classification_scores(observed, predicted, probabilities):
    """Scores after turning percentages into risk classes. `probabilities` has one column per class."""
    labels = [t["label"] for t in config.RISK_THRESHOLDS]
    observed, predicted = np.asarray(observed), np.asarray(predicted)
    precision, recall, f1, support = precision_recall_fscore_support(observed, predicted, labels=labels, zero_division=0)
    classes = []
    for i, label in enumerate(labels):
        target = observed == label
        auc = roc_auc_score(target, probabilities[label]) if 0 < target.sum() < len(target) else None
        classes.append({"label": label, "precision": round(float(precision[i]), 3), "recall": round(float(recall[i]), 3),
                        "f1": round(float(f1[i]), 3), "observed": int(support[i]),
                        "predicted": int((predicted == label).sum()),
                        "correct": int((target & (predicted == label)).sum()),
                        "roc_auc": None if auc is None else round(float(auc), 3)})
    aucs = [c["roc_auc"] for c in classes if c["roc_auc"] is not None]
    return {
        "n": int(len(observed)),
        "accuracy": round(float(accuracy_score(observed, predicted)), 3),
        "macro": {"precision": round(float(precision.mean()), 3), "recall": round(float(recall.mean()), 3),
                  "f1": round(float(f1.mean()), 3), "roc_auc": round(float(np.mean(aucs)), 3) if aucs else None},
        "classes": classes,
    }
