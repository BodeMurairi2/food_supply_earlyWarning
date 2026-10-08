# Step 4 – Staple food price features

**Script:** `pipeline/step04_prices.py`
**Input:** `data/prices/wfp_food_prices_rwa.csv` — WFP market prices for Rwanda from HDX (https://data.humdata.org/dataset/wfp-food-prices-for-rwanda), monthly, per market, 2008 – Aug 2026.
**Output:** `data/features/04_prices.csv` (630 rows)

## Commodities

Retail prices in RWF per kg for five staples: **beans (dry), maize, cassava flour, Irish potatoes, sorghum**.

## Features

| Column | Meaning |
|---|---|
| `price_<crop>_rwf_kg` | Average retail price over April t-1 to March t (RWF/kg) |
| `price_<crop>_yoy_pct` | % change from the same window one year earlier |
| `price_level` | Where the price came from: `district`, `province` or `national` (based on beans) |

## How

1. Keep retail prices sold by the kg; average markets per district, per province and nationally for each month.
2. Average each level over the 12-month window (at least 6 months of data required).
3. For each district take the most local level available: **district → province → national**.
4. The year-on-year change compares the window with the previous one at the same level.

## Coverage

| Years | Typical source |
|---|---|
| 2006–2008 | No data (WFP series starts in 2008) |
| 2009–2016 | District markets for 23–27 districts, province for the rest |
| 2017–2026 | Only 5–7 districts have markets; most use province (17–22) or national (3–10) averages |

## Limitations

- Prices are **nominal** (not adjusted for inflation). The year-on-year change removes most of the trend; consider dividing by NISR's CPI later.
- After 2016 most districts share their province value, so prices mostly separate provinces, not districts.
- WFP sometimes changes which markets it monitors, which can create jumps in province or national averages.
