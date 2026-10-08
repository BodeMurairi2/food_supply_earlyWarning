"""Step 4 - Staple food price features per district per target year.

Source: data/prices/wfp_food_prices_rwa.csv (WFP market monitoring via HDX), retail
prices in RWF per kg, monthly, per market, 2008-2026.

For target year t we use the 12 months April t-1 to March t (the year before a CFSVA
survey). WFP covers about 25-29 districts until 2015 but only 5-7 from 2016, so each
value comes from the most local level with at least 6 months of data:
district markets -> province markets -> national average. The level used is recorded
in price_level (taken from beans, the most widely reported staple).

Prices are nominal. The year-on-year change compares the same window one year earlier
at the same level, which removes most of the inflation trend.

Output: data/features/04_prices.csv
"""

import pandas as pd

from common import DATA, DISTRICTS, panel, save

COMMODITIES = {
    "Beans (dry)": "beans",
    "Maize": "maize",
    "Cassava flour": "cassava_flour",
    "Potatoes (Irish)": "irish_potato",
    "Sorghum": "sorghum",
}
MIN_MONTHS = 6
PROVINCE_FROM_WFP = {"Kigali City": "Kigali City", "Eastern Province": "Eastern Province", "Northern Province": "Northern Province",
                     "Southern Province": "Southern Province", "Western Province": "Western Province"}


def window_means(monthly, keys):
    """Average monthly price over April t-1 .. March t, keyed by target year t."""
    m = monthly.copy()
    m["year"] = (m["period"] - 3).dt.year + 1  # April t-1 .. March t -> t
    g = m.groupby(keys + ["commodity", "year"])["price"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] >= MIN_MONTHS].drop(columns="size").rename(columns={"mean": "price"})
    g = g.sort_values("year")
    g["prev"] = g.groupby(keys + ["commodity"])["price"].shift(1)
    prev_year = g.groupby(keys + ["commodity"])["year"].shift(1)
    g["yoy_pct"] = (100 * (g["price"] / g["prev"] - 1)).where(prev_year == g["year"] - 1)
    return g.drop(columns="prev")


def main():
    """Pick the most local staple price available (district, province, national) and save 04_prices.csv."""
    p = pd.read_csv(DATA / "prices" / "wfp_food_prices_rwa.csv", skiprows=[1])
    p = p[(p["pricetype"] == "Retail") & (p["unit"] == "KG") & p["commodity"].isin(COMMODITIES)]
    p["commodity"] = p["commodity"].map(COMMODITIES)
    p["period"] = pd.to_datetime(p["date"]).dt.to_period("M")
    p["province"] = p["admin1"].map(PROVINCE_FROM_WFP)
    p = p.rename(columns={"admin2": "district"})
    market = p.groupby(["province", "district", "market", "commodity", "period"])["price"].mean().reset_index()

    levels = {
        "district": window_means(market.groupby(["district", "commodity", "period"])["price"].mean().reset_index(), ["district"]),
        "province": window_means(market.groupby(["province", "commodity", "period"])["price"].mean().reset_index(), ["province"]),
        "national": window_means(market.groupby(["commodity", "period"])["price"].mean().reset_index(), []),
    }

    base = panel()
    out = base.copy()
    for name in COMMODITIES.values():
        chosen = base[["year", "province", "district"]].copy()
        chosen["price"] = pd.NA
        chosen["yoy_pct"] = pd.NA
        chosen["level"] = pd.NA
        for level, keys in [("district", ["district"]), ("province", ["province"]), ("national", [])]:
            v = levels[level]
            v = v[v["commodity"] == name].drop(columns="commodity")
            merged = chosen.merge(v, on=keys + ["year"], how="left", suffixes=("", "_new"))
            take = merged["price"].isna() & merged["price_new"].notna()
            chosen.loc[take.values, "price"] = merged.loc[take, "price_new"].values
            chosen.loc[take.values, "yoy_pct"] = merged.loc[take, "yoy_pct_new"].values
            chosen.loc[take.values, "level"] = level
        out[f"price_{name}_rwf_kg"] = pd.to_numeric(chosen["price"])
        out[f"price_{name}_yoy_pct"] = pd.to_numeric(chosen["yoy_pct"])
        if name == "beans":
            out["price_level"] = chosen["level"].values

    out = out.sort_values(["year", "district_pcode"]).round(2)
    print("price level used (beans):", out.groupby("year")["price_level"].agg(lambda s: s.value_counts().to_dict()).to_dict())
    feats = [c for c in out.columns if c.startswith("price_") and c != "price_level"]
    print("missing values per feature:", out[feats].isna().sum().to_dict())
    save(out, "04_prices.csv")


if __name__ == "__main__":
    main()
