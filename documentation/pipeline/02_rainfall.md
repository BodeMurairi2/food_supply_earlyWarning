# Step 2 – Rainfall features

**Script:** `pipeline/step02_rainfall.py`
**Input:** `data/rainfall/data/processed/rwanda_rainfall_district_monthly.csv` — CHIRPS monthly rainfall per district (1981 – Sep 2026), published by WFP on HDX, with long-term normals (1989–2018). See `data/rainfall/README.md` for how it was downloaded.
**Output:** `data/features/02_rainfall.csv` (630 rows, no missing values)

## Windows for target year t

Rwanda has two main seasons. For a survey around April of year t, the rains that matter are:

| Window | Months | Feeds |
|---|---|---|
| Season B rains | March–May of t-1 | Season B harvest (June–July of t-1) |
| Season A rains | September–December of t-1 | Season A harvest (January–February of t) |
| 12 months | March t-1 to February t | Everything above |

## Features

| Column | Meaning |
|---|---|
| `rain_12m_mm` | Total rainfall in the 12-month window (mm) |
| `rain_12m_pct_normal` | That total as % of the long-term normal |
| `rain_seasonB_mm`, `rain_seasonA_mm` | Seasonal rainfall totals (mm) |
| `rain_seasonB_pct_normal`, `rain_seasonA_pct_normal` | Seasonal totals as % of normal |
| `rain_seasonB_zscore`, `rain_seasonA_zscore` | Seasonal total compared with the district's 1981–2010 seasons, in standard deviations (a simple drought/flood index; below −1 is a dry season) |
| `rain_n_dry_months` | Rainy-season months with less than 60% of normal rain (drought signal) |
| `rain_n_wet_months` | Rainy-season months with more than 150% of normal rain (flood / landslide signal) |
| `rain_max_month_mm` | Wettest month in the window (mm) |

## How

1. Sum monthly rainfall and normals over each season, per district and year.
2. Compare each season with the same season in 1981–2010 for that district (mean and standard deviation) to get the z-score.
3. Shift seasons of year t-1 to target year t.
4. For the 12-month window, count dry and wet months and take the wettest month.

## Limitations

- CHIRPS is satellite + gauge rainfall on a ~5 km grid, averaged per district by WFP; very local storms are smoothed.
- The most recent months (September 2026) are preliminary.
