"""The fixed model context handed to the AI Analyst."""

from api import config
from api.data.serialization import clean
from api.services.forecasts import district_series
from api.services.model_insights import explain
from api.services.predictions import inputs_for, predict
from api.services.visualizations import viz_trends


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


def _prediction_context(ctx, req):
    if not req.district or req.year is None:
        raise ValueError("Choose a district and a year")
    result = predict(ctx, req.district, req.year, req.inputs)
    defaults = inputs_for(ctx, req.district, req.year)["inputs"]
    changed = []
    for feature, value in req.inputs.items():
        if feature in defaults and value != defaults[feature]:
            changed.append({"input": config.FEATURE_INFO.get(feature, (feature,))[0], "dataset_value": defaults[feature], "user_value": value})
    return {
        "district": req.district, "province": result["province"], "year": req.year,
        "model": {"name": f"Random forest, {result['model']}",
                  "target": "share of households moderately or severely food insecure (CARI), %",
                  "prediction_pct": result["prediction"], "risk_class": result["risk"],
                  "risk_thresholds": "Low < 15%, Medium 15-30%, High >= 30% (illustrative, not official NISR categories)",
                  "dataset_value_this_year": result["dataset_value_this_year"], "model_average_pct": round(result["base_value"], 1),
                  "typical_error_points": "MAE 5.4 on 2021/2024 real surveys"},
        "inputs_changed_by_user": changed,
        "inputs_left_empty_and_filled_by_the_model": result["missing_inputs_imputed"],
        "contributions": [{"feature": c["label"], "value": c["value"], "unit": c["unit"], "points": round(c["contribution"], 2)}
                          for c in result["contributions"][:8]],
        "survey_history": [{"year": h["year"], "pct": h["observed"], "type": h["observation_type"]} for h in result["history"]],
    }


def _visualization_context(ctx, req):
    if not req.variable:
        raise ValueError("Choose a variable")
    if not req.province and not req.district:
        raise ValueError("Choose a province or a district")
    ctx.dataset.validate_location(req.province, req.district)
    province = req.province
    if req.district and not province:
        districts = ctx.dataset.districts
        province = districts.loc[districts["district"] == req.district, "province"].iloc[0]
    trends = viz_trends(ctx, req.variable, req.level, province, req.district, req.start_year, req.end_year)
    # The model's forecasts for the same area, so the outlook can connect the trend to food insecurity.
    rows, _ = ctx.models.forecasts
    rows = ctx.dataset.filter_locations(rows, province, req.district)
    forecasts = {str(int(y)): round(float(g["predicted"].mean()), 1) for y, g in rows.groupby("year")}
    return {
        "area": req.district or province, "province": province,
        "variable": trends["variable"],
        "years": [req.start_year, req.end_year],
        "series": trends["series"],
        "rwanda": trends["national"] if trends["variable"]["aggregation"] == "mean" else None,
        "comparison": trends["comparison"],
        "incomplete_years": trends["partial_years"],
        "notes": trends["notes"],
        "model_forecast_food_insecure_pct_for_this_area": forecasts,
    }


def assistant_context(ctx, req):
    """The numbers the AI assistant may use, recomputed here so they cannot be altered by the browser."""
    if req.kind == "prediction":
        return _prediction_context(ctx, req)
    if req.kind == "forecast":
        if not req.district or req.year is None:
            raise ValueError("Choose a district and a year")
        if not config.FORECAST_YEARS[0] <= req.year <= config.FORECAST_YEARS[1]:
            raise ValueError("Forecasts are available for 2025-2026")
        return ai_context(ctx, req.district, req.year)
    return _visualization_context(ctx, req)
