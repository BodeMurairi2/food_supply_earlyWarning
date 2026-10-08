"""Step 1 - Target: district food insecurity (% of households) for every year 2006-2024.

1. CFSVA 2015, 2018, 2021, 2024: weighted % of households in CARI classes
   "moderately" or "severely food insecure" (the official NISR/WFP indicator).
2. CFSVA 2006, 2009, 2012 have no CARI class. We compute the Food Consumption Score
   (FCS), take the % of households with inadequate consumption (FCS <= 35), and convert
   it to a CARI-equivalent % with a linear fit learned on the 2015-2024 districts.
3. Years between surveys are linearly interpolated per district; years before a
   district's first survey are back-filled.

Outputs:
    data/features/01_target_survey_rounds.csv   one row per district per survey round
    data/features/01_target.csv                 one row per district per year (2006-2026)
"""

import numpy as np
import pandas as pd
import pyreadstat

from common import DATA, FIRST_YEAR, LAST_TARGET_YEAR, clean_district, district_from_code, panel, save

CFSVA = DATA / "CFSVA"
RISK_BINS = [-np.inf, 15, 30, np.inf]
RISK_LABELS = ["low", "medium", "high"]

# WFP Food Consumption Score: food group weights.
FCS_WEIGHTS = {"staples": 2, "pulses": 3, "vegetables": 1, "fruit": 1, "meat_fish": 4, "milk": 4, "sugar": 0.5, "oil": 0.5}
# Food items asked in CFSVA 2006 (q9_4_1..21) and 2009 (codes 94..114), same order in both rounds.
ITEM_GROUPS = [
    "staples", "staples", "staples", "staples", "staples", "staples", "staples", "staples",  # maize, rice, other cereals, cassava, sweet potato, other roots, bread/mandazi, cooking banana
    "pulses", "vegetables", "vegetables", "pulses", "pulses",  # beans/peas, other vegetables, cassava leaves, groundnuts, sunflower seeds
    "fruit", "meat_fish", "meat_fish", "meat_fish", "meat_fish",  # fruit, fish, meat, poultry, eggs
    "oil", "sugar", "milk",
]


def weighted_pct(df, flag, weight, by="district"):
    w = df[weight] if weight else pd.Series(1.0, index=df.index)
    tmp = df.assign(_w=w, _x=df[flag].astype(float) * w)
    g = tmp.groupby(by)
    return (100 * g["_x"].sum() / g["_w"].sum()).rename(flag), g.size().rename("n_households")


def fcs_from_days(days):
    """days: DataFrame with 21 item columns (days eaten in last 7 days) -> FCS per household."""
    days = days.where(days <= 7)  # codes above 7 are not valid day counts
    groups = days.T.groupby(ITEM_GROUPS).sum(min_count=1).T.clip(upper=7)
    return sum(groups[g].fillna(0) * w for g, w in FCS_WEIGHTS.items())


def cari_round(year, path, weight):
    d, _ = pyreadstat.read_sav(path, usecols=["S0_D_Dist", "FS_final", "FCS", weight], apply_value_formats=True)
    d = d.dropna(subset=["FS_final"]).assign(district=lambda x: x["S0_D_Dist"].map(clean_district))
    d["cari_insecure"] = d["FS_final"].astype(str).str.contains("insecure", case=False)
    d["fcs_inadequate"] = d["FCS"] <= 35
    cari, n = weighted_pct(d, "cari_insecure", weight)
    fcs, _ = weighted_pct(d.dropna(subset=["FCS"]), "fcs_inadequate", weight)
    return pd.concat([cari, fcs, n], axis=1).reset_index().assign(year=year, label_source="cari_survey")


def fcs_round_2012():
    d, _ = pyreadstat.read_sav(CFSVA / "2012" / "cfsvans-2012- household-v01.sav",
                               usecols=["d_code", "FCS", "FINAL_PopWeight"], apply_value_formats=True)
    d = d.dropna(subset=["FCS"]).assign(district=lambda x: x["d_code"].map(clean_district), fcs_inadequate=lambda x: x["FCS"] <= 35)
    fcs, n = weighted_pct(d, "fcs_inadequate", "FINAL_PopWeight")
    return pd.concat([fcs, n], axis=1).reset_index().assign(year=2012)


def fcs_round_2006():
    items = [f"q9_4_{i}" for i in range(1, 22)]
    d, _ = pyreadstat.read_sav(CFSVA / "2006" / "Data" / "June_10_Section1_11.sav", usecols=["distr06", "hhweight"] + items)
    d = d.dropna(subset=["distr06"])
    d["district"] = [district_from_code(c // 100, c % 100) for c in d["distr06"].astype(int)]
    d["FCS"] = fcs_from_days(d[items])
    d["fcs_inadequate"] = d["FCS"] <= 35
    fcs, n = weighted_pct(d, "fcs_inadequate", "hhweight")
    return pd.concat([fcs, n], axis=1).reset_index().assign(year=2006)


def fcs_round_2009():
    d, _ = pyreadstat.read_sav(CFSVA / "2009" / "Data" / "S9 Question.sav", usecols=["ID1", "ID2", "CODE_HH", "S9Q3J", "S9Q3L"])
    d = d[d["S9Q3J"].between(94, 114)]  # 21 food items; 115 (spices) is not part of the FCS
    days = d.pivot_table(index=["ID1", "ID2", "CODE_HH"], columns="S9Q3J", values="S9Q3L", aggfunc="max")
    days = days.reindex(columns=range(94, 115))
    hh = days.index.to_frame(index=False)
    hh["district"] = [district_from_code(p, n) for p, n in zip(hh["ID1"], hh["ID2"])]
    hh["FCS"] = fcs_from_days(days.reset_index(drop=True).set_axis(range(21), axis=1)).values
    hh["fcs_inadequate"] = hh["FCS"] <= 35
    fcs, n = weighted_pct(hh, "fcs_inadequate", None)  # 2009 file has no weights; sample was allocated by district
    return pd.concat([fcs, n], axis=1).reset_index().assign(year=2009)


def main():
    cari = pd.concat([
        cari_round(2015, CFSVA / "2015" / "cfsva-2015-master-DB- annex.sav", "weight"),
        cari_round(2018, CFSVA / "2018" / "1_CFSVA18_DB_HouseholdQues_Full_Annex_201904_NISR.sav", "FinalWeight"),
        cari_round(2021, CFSVA / "2021" / "Microdata" / "CFSVA_HH_2021_MASTER_DATASET.sav", "FinalWeight"),
        cari_round(2024, CFSVA / "2024" / "Microdata" / "spss" / "CFSVA2024_HH.sav", "FinalWeight"),
    ]).rename(columns={"cari_insecure": "food_insecure_pct", "fcs_inadequate": "fcs_inadequate_pct"})

    # Calibrate FCS -> CARI on the rounds that have both.
    slope, intercept = np.polyfit(cari["fcs_inadequate_pct"], cari["food_insecure_pct"], 1)
    pred = intercept + slope * cari["fcs_inadequate_pct"]
    r = np.corrcoef(cari["fcs_inadequate_pct"], cari["food_insecure_pct"])[0, 1]
    mae = (pred - cari["food_insecure_pct"]).abs().mean()
    print(f"FCS->CARI calibration: food_insecure_pct = {slope:.3f} * fcs_inadequate_pct + {intercept:.2f} (r={r:.3f}, MAE={mae:.2f} pts, n={len(cari)})")

    proxy = pd.concat([fcs_round_2006(), fcs_round_2009(), fcs_round_2012()]).rename(columns={"fcs_inadequate": "fcs_inadequate_pct"})
    proxy["food_insecure_pct"] = (intercept + slope * proxy["fcs_inadequate_pct"]).clip(lower=0)
    proxy["label_source"] = "fcs_proxy_survey"

    rounds = pd.concat([proxy, cari], ignore_index=True)
    rounds = rounds[rounds["district"].notna()]
    rounds = panel().merge(rounds, on=["year", "district"], how="inner")
    rounds = rounds[["year", "province", "district", "district_pcode", "food_insecure_pct", "fcs_inadequate_pct", "n_households", "label_source"]]
    rounds = rounds.sort_values(["year", "district_pcode"]).round(2)
    for y, g in rounds.groupby("year"):
        print(f"  {y}: {len(g)} districts, {g['label_source'].iloc[0]}, mean {g['food_insecure_pct'].mean():.1f}%")
    save(rounds, "01_target_survey_rounds.csv")

    # Yearly series: interpolate between surveys, back-fill before the first survey.
    out = panel().merge(rounds[["year", "district", "food_insecure_pct", "label_source"]], on=["year", "district"], how="left")
    out["is_survey_year"] = out["label_source"].notna()
    in_range = out["year"].between(FIRST_YEAR, LAST_TARGET_YEAR)
    parts = []
    for _, g in out.groupby("district"):
        g = g.sort_values("year").copy()
        m = g["year"].between(FIRST_YEAR, LAST_TARGET_YEAR)
        s = g.loc[m, "food_insecure_pct"]
        filled = s.interpolate(method="linear", limit_area="inside")
        g.loc[m & s.isna() & filled.notna(), "label_source"] = "interpolated"
        filled = filled.bfill()
        g.loc[m & g["label_source"].isna() & filled.notna(), "label_source"] = "backfilled"
        g.loc[m, "food_insecure_pct"] = filled
        # Most recent real survey value strictly before year t (safe to use as a forecasting feature).
        surveys = g["food_insecure_pct"].where(g["is_survey_year"])
        g["last_survey_food_insecure_pct"] = surveys.shift(1).ffill()
        parts.append(g)
    out = pd.concat(parts)
    out.loc[~in_range, "label_source"] = "forecast_no_target"
    out["risk_class"] = pd.cut(out["food_insecure_pct"], RISK_BINS, labels=RISK_LABELS, right=False)
    out = out.sort_values(["year", "district_pcode"])[
        ["year", "province", "district", "district_pcode", "food_insecure_pct", "risk_class", "label_source", "is_survey_year", "last_survey_food_insecure_pct"]
    ].round(2)
    has_target = out["year"].between(FIRST_YEAR, LAST_TARGET_YEAR)
    print(out[has_target]["label_source"].value_counts().to_dict(), "| risk classes:", out[has_target]["risk_class"].value_counts().to_dict())
    save(out, "01_target.csv")


if __name__ == "__main__":
    main()
