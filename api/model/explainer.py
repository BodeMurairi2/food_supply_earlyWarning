"""SHAP explanations for the saved pipelines."""

import numpy as np
import pandas as pd
import shap

from api import config
from api.data.serialization import clean


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


def feature_label(feature):
    return config.FEATURE_INFO.get(feature, (feature, "Other", ""))[0]


def contribution_items(shap_row, values_row, top=None):
    items = []
    for feature, contribution in shap_row.items():
        label, group, unit = config.FEATURE_INFO.get(feature, (feature, "Other", ""))
        value = values_row.get(feature)
        items.append({"feature": feature, "label": label, "group": group, "unit": unit,
                      "value": clean(value), "contribution": round(float(contribution), 3)})
    items.sort(key=lambda d: abs(d["contribution"]), reverse=True)
    return items[:top] if top else items
