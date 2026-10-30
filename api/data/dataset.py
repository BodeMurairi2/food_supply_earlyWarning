"""The district-year dataset and district boundaries, loaded once from local files."""

import json

import numpy as np
import pandas as pd

from api import config

LABEL_SOURCE_NAMES = {
    "cari_survey": "Survey (CARI)",
    "fcs_proxy_survey": "Survey estimate (FCS)",
    "interpolated": "Interpolated",
    "backfilled": "Back-filled",
    "forecast_no_target": "No survey",
}


class Dataset:
    def __init__(self):
        # The notebook replaces the one infinite value (a yield change after a zero yield) with NaN.
        self.df = pd.read_csv(config.DATASET_PATH).replace([np.inf, -np.inf], np.nan)
        self.boundaries = json.loads(config.BOUNDARIES_PATH.read_text())
        self.districts = (self.df[["province", "district"]].drop_duplicates()
                          .sort_values(["province", "district"]).reset_index(drop=True))

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
