"""Turn pandas and numpy values into JSON-safe Python values."""

import math

import numpy as np


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
