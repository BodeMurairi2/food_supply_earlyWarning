"""The fixed model context handed to the AI Analyst."""

from api import config
from api.data.serialization import clean
from api.services.forecasts import district_series
from api.services.model_insights import explain


def ai_context(ctx, district, year):
    """Everything the AI Analyst may use about one district-year, straight from the model and dataset."""
    e = explain(ctx, district, year)
    series = district_series(ctx, district)["series"]
    d = ctx.dataset.df[ctx.dataset.df["district"] == district].set_index("year")
    recent = []
    for y in range(max(2006, year - 3), year + 1):
        if y not in d.index:
            continue
        r = d.loc[y]
        recent.append({"year": y,
                       "rain_pct_of_normal": clean(r["rain_12m_pct_normal"]),
                       "dry_months": clean(r["rain_n_dry_months"]),
                       "temp_anomaly_c": clean(r["temp_12m_anomaly_c"]),
                       **{f"{c}_yield_kg_ha": clean(r[f"sas_{c}_yield_kg_ha"]) for c in config.STAPLE_CROPS},
                       "beans_price_rwf_kg": clean(r["price_beans_rwf_kg"]),
                       "maize_price_rwf_kg": clean(r["price_maize_rwf_kg"])})
    fc, _ = ctx.models.forecasts
    fc = fc[fc["district"] == district].set_index("year")["predicted"]
    return {
        "district": district, "province": e["province"], "year": year,
        "model": {"name": f"Random forest, {e['model']}",
                  "target": "share of households moderately or severely food insecure (CARI), %",
                  "prediction_pct": round(e["prediction"], 1), "risk_class": e["risk"],
                  "risk_thresholds": "Low < 15%, Medium 15-30%, High >= 30% (illustrative, not official NISR categories)",
                  "observed_pct_this_year": e["observed"], "model_average_pct": round(e["base_value"], 1),
                  "typical_error_points": "MAE 5.4 on 2021/2024 real surveys",
                  "forecasts": {str(int(y)): round(float(v), 1) for y, v in fc.items()}},
        "contributions": [{"feature": c["label"], "value": c["value"], "unit": c["unit"],
                           "points": round(c["contribution"], 2)} for c in e["contributions"][:8]],
        "survey_history": [{"year": p["year"], "pct": p["observed"], "type": p["observation_type"]}
                           for p in series if p["observation_type"] in ("Survey (CARI)", "Survey estimate (FCS)")],
        "recent_inputs": recent,
        "data_notes": [e["note"],
                       "Each year covers April of the year before to March of that year.",
                       *([config.SAS_PARTIAL_YEARS[year]] if year in config.SAS_PARTIAL_YEARS else [])],
    }
