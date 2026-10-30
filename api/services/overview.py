"""Overview dashboard: summary cards, risk map, yearly trend and top districts."""

from api import config
from api.data.dataset import LABEL_SOURCE_NAMES
from api.data.serialization import clean, records
from api.model.metrics import risk_class


def value_for_year(ctx, year):
    """Per-district value for a year: observed/estimated up to 2024, forecast for 2025-2026."""
    if year in range(config.FORECAST_YEARS[0], config.FORECAST_YEARS[1] + 1):
        rows, _ = ctx.models.forecasts
        rows = rows[rows["year"] == year]
        out = rows[["province", "district"]].copy()
        out["value"] = rows["predicted"].values
        out["value_type"] = "Forecast"
    else:
        rows = ctx.dataset.df[ctx.dataset.df["year"] == year]
        out = rows[["province", "district"]].copy()
        out["value"] = rows[ctx.models.target].values
        out["value_type"] = rows["label_source"].map(LABEL_SOURCE_NAMES).values
    out["risk"] = out["value"].map(risk_class)
    return out


def overview(ctx, province=None, district=None, year=2025):
    ctx.dataset.validate_location(province, district)
    values = value_for_year(ctx, year)
    selected = ctx.dataset.filter_locations(values, province, district)
    counts = {t["label"]: int((selected["risk"] == t["label"]).sum()) for t in config.RISK_THRESHOLDS}

    latest = ctx.dataset.filter_locations(ctx.dataset.df[ctx.dataset.df["label_source"] == "cari_survey"], province, district)
    latest_year = int(latest["year"].max())
    latest_avg = latest.loc[latest["year"] == latest_year, ctx.models.target].mean()

    fc_rows, _ = ctx.models.forecasts
    fc_rows = ctx.dataset.filter_locations(fc_rows, province, district)
    forecast_avg = {str(int(y)): clean(g["predicted"].mean()) for y, g in fc_rows.groupby("year")}

    # Yearly trend (simple average over the selected districts)
    base = ctx.dataset.filter_locations(ctx.dataset.df, province, district)
    trend = []
    for y, g in base.groupby("year"):
        y = int(y)
        if y >= config.FORECAST_YEARS[0]:
            fi = fc_rows[fc_rows["year"] == y]["predicted"].mean()
            kind = "Forecast"
        else:
            fi = g[ctx.models.target].mean()
            kind = "Survey" if (g["label_source"] == "cari_survey").any() else (
                "Survey estimate" if (g["label_source"] == "fcs_proxy_survey").any() else "Interpolated")
        trend.append({"year": y, "food_insecure_pct": clean(fi), "value_type": kind,
                      "rain_pct_normal": clean(g["rain_12m_pct_normal"].mean()),
                      "temp_anomaly_c": clean(g["temp_12m_anomaly_c"].mean()),
                      "maize_yield_kg_ha": clean(g["sas_maize_yield_kg_ha"].mean()),
                      "beans_yield_kg_ha": clean(g["sas_beans_yield_kg_ha"].mean())})

    top = selected.sort_values("value", ascending=False).head(10)
    return {
        "filters": {"province": province, "district": district, "year": year},
        "n_districts": int(selected.shape[0]),
        "latest_survey": {"year": latest_year, "avg_food_insecure_pct": clean(latest_avg)},
        "forecast_avg": forecast_avg,
        "selected_year": {"year": year, "value_type": "Forecast" if year >= config.FORECAST_YEARS[0] else "Observed or estimated",
                          "avg_food_insecure_pct": clean(selected["value"].mean()), "risk_counts": counts},
        "map": records(values.assign(selected=values["district"].isin(selected["district"]))),
        "trend": trend,
        "top_districts": records(top),
        "note": "Province and national figures are simple averages of district values.",
    }
