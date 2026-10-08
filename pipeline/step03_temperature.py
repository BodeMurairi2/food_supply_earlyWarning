"""Step 3 - Temperature features per district per target year.

Source: data/processed/temperature_monthly_district.csv
(ERA5-Land monthly mean 2 m air temperature per district, 1995-2026; built by
process_temperature.py, see documentation/temperature_data_approach.docx).

Same windows as the rainfall step: Season B (March-May of t-1), Season A
(September-December of t-1) and the 12 months March t-1 to February t. Anomalies are
differences from the district's 1995-2024 average for the same window.

Output: data/features/03_temperature.csv
"""

import pandas as pd

from common import DATA, panel, save

SEASONS = {"seasonB": [3, 4, 5], "seasonA": [9, 10, 11, 12]}
BASELINE = (1995, 2024)


def main():
    """Compute seasonal and 12-month temperature features and anomalies and save 03_temperature.csv."""
    t = pd.read_csv(DATA / "processed" / "temperature_monthly_district.csv")[["district", "year", "month", "temp_mean_c"]]

    parts = []
    for name, months in SEASONS.items():
        s = t[t["month"].isin(months)].groupby(["district", "year"])["temp_mean_c"].agg(["mean", "size"]).reset_index()
        s = s[s["size"] == len(months)].rename(columns={"mean": f"temp_{name}_c"})
        clim = s[s["year"].between(*BASELINE)].groupby("district")[f"temp_{name}_c"].mean().rename("clim")
        s = s.join(clim, on="district")
        s[f"temp_{name}_anomaly_c"] = s[f"temp_{name}_c"] - s["clim"]
        s["year"] += 1  # season of t-1 -> target year t
        parts.append(s[["district", "year", f"temp_{name}_c", f"temp_{name}_anomaly_c"]].set_index(["district", "year"]))
    seasonal = pd.concat(parts, axis=1).reset_index()

    t["period"] = pd.PeriodIndex.from_fields(year=t["year"], month=t["month"], freq="M")
    t["target_year"] = (t["period"] - 2).dt.year + 1  # March t-1 .. February t -> t
    w = t.groupby(["district", "target_year"])["temp_mean_c"].agg(temp_12m_c="mean", temp_max_month_c="max", n="size").reset_index()
    w = w[w["n"] == 12].drop(columns="n").rename(columns={"target_year": "year"})
    clim = w[w["year"].between(*BASELINE)].groupby("district")["temp_12m_c"].mean().rename("clim")
    w = w.join(clim, on="district")
    w["temp_12m_anomaly_c"] = w["temp_12m_c"] - w["clim"]
    w = w.drop(columns="clim")

    out = panel().merge(w, on=["district", "year"], how="left").merge(seasonal, on=["district", "year"], how="left")
    out = out.sort_values(["year", "district_pcode"]).round(2)
    feats = [c for c in out.columns if c.startswith("temp_")]
    print("missing values per feature:", out[feats].isna().sum().to_dict())
    save(out, "03_temperature.csv")


if __name__ == "__main__":
    main()
