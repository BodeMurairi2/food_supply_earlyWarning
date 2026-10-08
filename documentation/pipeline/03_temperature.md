# Step 3 – Temperature features

**Script:** `pipeline/step03_temperature.py`
**Input:** `data/processed/temperature_monthly_district.csv` — ERA5-Land monthly mean 2 m air temperature per district, 1995 – Sep 2026. How it was built and validated against NISR stations is in `documentation/temperature_data_approach.docx` (scripts `download_scripts/download_era5_land.py`, `pipeline/process_temperature.py`).
**Output:** `data/features/03_temperature.csv` (630 rows, no missing values)

## Features

Same windows as rainfall (Season B = March–May of t-1, Season A = September–December of t-1, 12 months = March t-1 to February t).

| Column | Meaning |
|---|---|
| `temp_12m_c` | Mean temperature over the 12-month window (°C) |
| `temp_12m_anomaly_c` | Difference from the district's 1995–2024 average for the same window (°C) |
| `temp_max_month_c` | Warmest month in the window (°C) |
| `temp_seasonB_c`, `temp_seasonA_c` | Seasonal mean temperature (°C) |
| `temp_seasonB_anomaly_c`, `temp_seasonA_anomaly_c` | Seasonal difference from the district's 1995–2024 average (°C) |

## How

1. Average monthly temperature over each season, per district and year (only complete seasons).
2. Subtract the district's 1995–2024 average for the same season → anomaly.
3. Shift seasons of t-1 to target year t; build the 12-month window the same way.

## Limitations

- ERA5-Land runs about 1.4 °C cooler than NISR stations (see the temperature document). Anomalies remove this offset, so prefer the `_anomaly_c` columns.
- 2026 values come from preliminary data (ERA5-LandT).
