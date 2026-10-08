"""Step 2 - Rainfall features per district per target year.

Source: data/rainfall/data/processed/rwanda_rainfall_district_monthly.csv
(CHIRPS monthly rainfall per district, 1981-2026, with WFP long-term normals 1989-2018).

For target year t (survey around April of t) the relevant rains are:
    Season B rains: March-May of t-1   (Season B harvest, June-July of t-1)
    Season A rains: September-December of t-1 (Season A harvest, January-February of t)
All features use only months before April of t.

Output: data/features/02_rainfall.csv
"""

import pandas as pd

from common import DATA, panel, save

SEASONS = {"seasonB": [3, 4, 5], "seasonA": [9, 10, 11, 12]}  # months of year t-1
BASELINE = (1981, 2010)


def main():
    """Compute seasonal and 12-month rainfall features per district and year and save 02_rainfall.csv."""
    r = pd.read_csv(DATA / "rainfall" / "data" / "processed" / "rwanda_rainfall_district_monthly.csv")
    r = r[["district", "year", "month_num", "rain_mm", "normal_mm"]]

    # Seasonal totals by district and calendar year, with z-scores against 1981-2010.
    season_rows = []
    for name, months in SEASONS.items():
        s = r[r["month_num"].isin(months)].groupby(["district", "year"])[["rain_mm", "normal_mm"]].sum().reset_index()
        base = s[s["year"].between(*BASELINE)].groupby("district")["rain_mm"].agg(["mean", "std"])
        s = s.join(base, on="district")
        s[f"rain_{name}_mm"] = s["rain_mm"]
        s[f"rain_{name}_pct_normal"] = 100 * s["rain_mm"] / s["normal_mm"]
        s[f"rain_{name}_zscore"] = (s["rain_mm"] - s["mean"]) / s["std"]
        season_rows.append(s[["district", "year"] + [c for c in s.columns if c.startswith(f"rain_{name}")]].set_index(["district", "year"]))
    seasonal = pd.concat(season_rows, axis=1).reset_index()
    seasonal["year"] += 1  # rains of year t-1 belong to target year t

    # 12-month window March t-1 .. February t (all rains feeding Season B t-1 and Season A t).
    r["period"] = pd.PeriodIndex.from_fields(year=r["year"], month=r["month_num"], freq="M")
    r["target_year"] = (r["period"] - 2).dt.year + 1  # Mar t-1 .. Feb t -> t
    rainy = r["month_num"].isin([3, 4, 5, 9, 10, 11, 12])
    r["dry_month"] = rainy & (r["rain_mm"] < 0.6 * r["normal_mm"])
    r["wet_month"] = rainy & (r["rain_mm"] > 1.5 * r["normal_mm"])
    w = r.groupby(["district", "target_year"]).agg(
        rain_12m_mm=("rain_mm", "sum"), normal_12m_mm=("normal_mm", "sum"), n_months=("rain_mm", "size"),
        rain_n_dry_months=("dry_month", "sum"), rain_n_wet_months=("wet_month", "sum"), rain_max_month_mm=("rain_mm", "max"),
    ).reset_index().rename(columns={"target_year": "year"})
    w = w[w["n_months"] == 12]
    w["rain_12m_pct_normal"] = 100 * w["rain_12m_mm"] / w["normal_12m_mm"]
    w = w.drop(columns=["normal_12m_mm", "n_months"])

    out = panel().merge(w, on=["district", "year"], how="left").merge(seasonal, on=["district", "year"], how="left")
    out = out.sort_values(["year", "district_pcode"]).round(2)
    feats = [c for c in out.columns if c.startswith("rain_")]
    print("missing values per feature:", out[feats].isna().sum().to_dict())
    save(out, "02_rainfall.csv")


if __name__ == "__main__":
    main()
