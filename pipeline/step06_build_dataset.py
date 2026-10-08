"""Step 6 - Merge the target and all feature steps into one modelling table.

Inputs:  data/features/01_target.csv, 02_rainfall.csv, 03_temperature.csv, 04_prices.csv, 05_sas.csv
Output:  food_security_dataset.csv (repository root), one row per district per year 2006-2026.

Rows for 2006-2024 carry the target; rows for 2025-2026 carry features only and are the
years to forecast.
"""

import pandas as pd

from common import FEATURES, ROOT

KEYS = ["year", "province", "district", "district_pcode"]
STEPS = ["02_rainfall.csv", "03_temperature.csv", "04_prices.csv", "05_sas.csv"]


def main():
    """Merge the target and all feature tables into food_security_dataset.csv and print feature coverage."""
    df = pd.read_csv(FEATURES / "01_target.csv")
    for name in STEPS:
        step = pd.read_csv(FEATURES / name)
        before = len(df)
        df = df.merge(step, on=KEYS, how="left", validate="one_to_one")
        assert len(df) == before, name
    df = df.sort_values(["year", "district_pcode"])

    out = ROOT / "food_security_dataset.csv"
    df.to_csv(out, index=False)
    feature_cols = [c for c in df.columns if c.startswith(("rain_", "temp_", "price_", "sas_")) and c != "price_level"]
    has_target = df["food_insecure_pct"].notna()
    print(f"Wrote {out.name}: {len(df)} rows ({has_target.sum()} with target), {len(feature_cols)} features, {df.shape[1]} columns")
    coverage = df.groupby("year")[feature_cols].apply(lambda g: g.notna().mean().mean() * 100).round(0)
    print("feature coverage % by year:", coverage.to_dict())


if __name__ == "__main__":
    main()
