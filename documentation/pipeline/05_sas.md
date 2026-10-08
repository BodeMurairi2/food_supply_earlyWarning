# Step 5 – Agriculture features from the Seasonal Agricultural Survey (SAS)

**Script:** `pipeline/step05_sas.py`
**Input:** NISR SAS plot-level microdata, `data/sas/<year>/` (Stata `.dta` files), 2013–2025, Seasons A, B and C.
**Code:** `pipeline/step05_sas.py` (2017–2025) and `pipeline/sas_legacy.py` (2013–2016, older questionnaire).
**Outputs:**
- `data/features/05_sas.csv` — one row per district per target year (the features)
- `data/features/05_sas_district_season.csv` — intermediate sums per district per season (useful for checking)
- `data/features/05_sas_variables_found.csv` — which column was used for each variable, per year and season (audit)

## Window for target year t

Season B and Season C of t-1 plus Season A of t: the harvests of the 12 months before a CFSVA survey. Example: target 2021 uses SAS 2020 B, 2020 C and 2021 A.

## Features

| Column | Meaning |
|---|---|
| `sas_<crop>_yield_kg_ha` | Yield: total harvest ÷ total crop area (kg/ha) |
| `sas_<crop>_production_t` | Estimated production (tonnes, survey-weighted) |
| `sas_<crop>_area_ha` | Estimated crop area (ha, survey-weighted) |
| `sas_<crop>_yield_change_pct` | Yield change from the previous year (maize, beans, cassava, Irish potato) |
| `sas_improved_seed_pct` | % of crop plots sown with improved seed |
| `sas_inorganic_fert_plots_pct` | % of plots that received inorganic fertilizer |
| `sas_inorganic_kg_ha`, `sas_dap_kg_ha`, `sas_urea_kg_ha`, `sas_npk_kg_ha` | Inorganic fertilizer used per hectare of surveyed plots: total and by type |
| `sas_sold_pct` | % of harvest sold (see note on how it is computed) |
| `sas_worse_harvest_pct` | % of crop plots where the farmer said the harvest was worse than last year (2022 onwards) |
| `sas_n_seasons` | Number of SAS seasons in the window |

Crops: maize, beans (bush and climbing), cassava, Irish potato, sweet potato, sorghum, banana (all types), rice.

## How

The column names change almost every year (e.g. harvest is `s2q22` in 2017 and `s2q21` later; fertilizer is one row per type in 2022 but several columns per plot in 2023 and 2025). So the script **finds each variable by its question label** (for example "Total quantity of harvest … (in Kg)") instead of its name, and logs the result in `05_sas_variables_found.csv`.

Per season and district:
1. **Production file:** crop (from the crop-name labels), harvest in kg, crop area, seed type, quantity sold, comparison with last year, and the plot weight.
   - **Crop area**, best available: harvested area (2018, 2019, 2022, 2023) → crop area (2017) → developed crop area (2020) → plot area ÷ number of crops on the plot (2021, 2024, 2025). The unit (m² or ha) comes from the label, or from the size of the values when the label does not say.
2. **Fertilizer file:** whether inorganic fertilizer was used on the plot; for each fertilizer entry its type (DAP / Urea / NPK), unit and quantity. Only kg and g are converted; litres and cc are left out.
3. Multiply by the plot weight (when the year has one) and sum per district.

Per target year: add the sums of the three seasons, then divide (e.g. kg ÷ ha for yield).

**Check against NISR reports (2024 Season A):** maize ≈ 2.4 t/ha (report: ~2 t/ha), Irish potato ≈ 10 t/ha (report: 8.5), and fertilizer types dominated by DAP and Urea, as in the reports.

## 2013–2016 (older questionnaire), `sas_legacy.py`

These rounds use a different layout (`farmq_part1`, `part2b`, `part4`, `screening` files in 2014–2016; numbered files such as `03_SSF_Pure_mixed_Crop_Land.dta` in 2013):

- **District:** not a column; it is the first two digits of the household or tract ID (e.g. `571124067` → 57 = Bugesera).
- **No harvest quantities per district.** Harvest uses (sold, eaten, stored…) are recorded as **percentages of the harvest**, not kg, and NISR only published production as national (`Yield.dta`) and, for 2013, province totals. So **production, yield and yield change cannot be computed for 2013–2016**.
- **Fertilizer** is recorded as used / not used and type, **without quantities**, so the kg/ha features are empty.

What these rounds add per district: **crop area** (ha, survey-weighted, from the screening files), **% improved seed**, **% plots with inorganic fertilizer**, and **% of harvest sold** (average of the reported percentages). Large-farm files (`lsf_*`, `*_BIG`) are skipped.

**2013 Season A is skipped:** its IDs encode province and stratum, not district (the first two digits give only 11, 22, 33, 44, 55), so its data cannot be placed in districts. As a result target year 2013 has no SAS features (it would need 2012 B/C and 2013 A); SAS features start at target year 2014.

## Note on `sas_sold_pct`

"Quantity sold" is reported per crop **for all of the farmer's plots**, while the harvest is per plot (in 20–25% of rows the quantity sold is larger than the plot's harvest). The share sold per crop record is therefore sold ÷ the farmer's all-plots production of that crop (when that question exists, 2019 and 2022+) or ÷ the plot harvest otherwise, capped at 100%. The feature is the **average share sold per crop record**, which is also how 2013–2016 report it (as percentages), so the series uses one definition for all years.

## Limitations

- **2013–2016 have no production, yield or fertilizer quantities** (see above); 2013 Season A is unusable.
- **2017–2018 use small-scale farm files only** (large farms are in separate files). 2017–2019 production files have **no survey weights**, so production and area totals are left empty for target years using them; yields and percentages are kept.
- `sas_improved_seed_pct` is a share of **crop plots**, lower than the report's share of **farmers** (e.g. 14% vs. 40% in 2024 A).
- Area defined as plot ÷ number of crops (2021, 2024, 2025) is an approximation for mixed plots.
- Season C (marshlands) is small and noisy, especially for fertilizer per hectare.
