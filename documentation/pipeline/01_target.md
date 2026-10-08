# Step 1 – Target: district food insecurity, 2006–2024

**Script:** `pipeline/step01_target.py`
**Outputs:**
- `data/features/01_target_survey_rounds.csv` – one row per district per survey round (206 rows)
- `data/features/01_target.csv` – one row per district per year, 2006–2026 (630 rows)

## What the target is

`food_insecure_pct`: the share of households in the district that are **moderately or severely food insecure**, using WFP's CARI method (Consolidated Approach for Reporting Indicators of Food Security). This is the official headline indicator of NISR's CFSVA (Comprehensive Food Security and Vulnerability Analysis).

`risk_class` turns it into three classes for classification: **low** (< 15%), **medium** (15–30%), **high** (≥ 30%).

## How it was built

### 1. Real CARI values: 2015, 2018, 2021, 2024 (120 rows)

From the CFSVA household microdata (`data/CFSVA/<year>/`):

| Year | File | Columns used |
|---|---|---|
| 2015 | `cfsva-2015-master-DB- annex.sav` | `S0_D_Dist`, `FS_final`, `weight` |
| 2018 | `1_CFSVA18_DB_HouseholdQues_Full_Annex_201904_NISR.sav` | `S0_D_Dist`, `FS_final`, `FinalWeight` |
| 2021 | `Microdata/CFSVA_HH_2021_MASTER_DATASET.sav` | `S0_D_Dist`, `FS_final`, `FinalWeight` |
| 2024 | `Microdata/spss/CFSVA2024_HH.sav` | `S0_D_Dist`, `FS_final`, `FinalWeight` |

For each district: weighted % of households whose `FS_final` is "Moderately food insecure" or "Severely food insecure". The survey weights make the result represent all households, not just the sampled ones.

**Check:** the results match the district tables published in the CFSVA reports (average difference 0.3 points in 2015, 0.02–0.03 in 2018 and 2021). 2024 matches the report's text (Nyamasheke 38%, Nyamagabe 35%).

### 2. Estimated values: 2006, 2009, 2012 (86 rows)

These rounds have no CARI class, but they do have the **Food Consumption Score (FCS)**, one of the inputs of CARI:

- **2012:** FCS is in the file (`cfsvans-2012- household-v01.sav`, column `FCS`, weight `FINAL_PopWeight`, district `d_code`).
- **2006:** computed from the number of days in the last 7 that each of 21 foods was eaten (`q9_4_1` … `q9_4_21`, weight `hhweight`, district code `distr06`, e.g. 507 = Eastern Province, district 7 = Bugesera).
- **2009:** computed from Section 9 (`S9 Question.sav`): `S9Q3J` = food code (94–114), `S9Q3L` = days eaten. District = province `ID1` + district number `ID2`. The file has no weights, so district shares are unweighted.

FCS uses WFP's standard weights: cereals and roots ×2, pulses and nuts ×3, vegetables ×1, fruit ×1, meat/fish/eggs ×4, milk ×4, oil ×0.5, sugar ×0.5 (days per group capped at 7).

For each district we take the % of households with **inadequate consumption (FCS ≤ 35)** and convert it to a CARI-equivalent with a straight line fitted on the 120 districts of 2015–2024, where both are known:

```
food_insecure_pct = 0.784 × fcs_inadequate_pct + 1.08     (r = 0.93, mean error ±3.2 points)
```

**Missing districts:** 2006 has 29 (no Nyarugenge); 2009 has 27 (no Kigali City districts, rural-only survey).

### 3. Years between surveys

For each district, values between two surveys are **linearly interpolated**. Nyarugenge 2006–2011 (before its first survey in 2012) is **back-filled** with the 2012 value.

## Columns of `01_target.csv`

| Column | Meaning |
|---|---|
| `year`, `province`, `district`, `district_pcode` | Keys (pcode = NISR code, e.g. RW57) |
| `food_insecure_pct` | Target, % of households food insecure |
| `risk_class` | low / medium / high |
| `label_source` | `cari_survey` (120), `fcs_proxy_survey` (86), `interpolated` (358), `backfilled` (6), `forecast_no_target` (2025–2026) |
| `is_survey_year` | True when the value comes directly from a survey round |
| `last_survey_food_insecure_pct` | The district's value at the **previous** survey round, safe to use as a feature (it is known before year t) |

## Limitations

- Interpolated years are estimates, not observations. Evaluate models on survey rows (`label_source == "cari_survey"`).
- The FCS-based values are a proxy; CARI also includes food spending and coping strategies.
- Survey months differ between rounds (March to June), which affects consumption.
- Do **not** use `food_insecure_pct` of neighbouring years as a feature: interpolated values contain information from the next survey.
