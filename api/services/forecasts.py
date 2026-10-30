"""Forecasts for 2025-2026 and the full history of one district."""

from api.data.dataset import LABEL_SOURCE_NAMES
from api.data.serialization import clean
from api.model.explainer import contribution_items
from api.model.metrics import risk_class


def forecast_table(ctx, province=None, district=None, top_drivers=3):
    ctx.dataset.validate_location(province, district)
    rows, shap_values = ctx.models.forecasts
    observed_2024 = ctx.dataset.df[ctx.dataset.df["year"] == 2024].set_index("district")[ctx.models.target]
    out = []
    for d, g in ctx.dataset.filter_locations(rows, province, district).groupby("district"):
        entry = {"province": g["province"].iloc[0], "district": d, "observed_2024": clean(observed_2024.get(d))}
        for _, r in g.iterrows():
            y = int(r["year"])
            drivers = contribution_items(shap_values.loc[r.name], r, top=top_drivers)
            entry[f"predicted_{y}"] = clean(r["predicted"])
            entry[f"risk_{y}"] = risk_class(r["predicted"])
            entry[f"drivers_{y}"] = [{"label": x["label"], "contribution": x["contribution"]} for x in drivers]
        out.append(entry)
    return {
        "rows": out,
        "status": {
            "2025": "Complete inputs: rainfall, temperature and prices to March 2025; harvests B/C 2024 and A 2025.",
            "2026": "Season A 2026 harvest data (SAS) is not published yet; agriculture inputs use Seasons B and C 2025 only.",
        },
        "note": "No CFSVA survey exists for 2025 or 2026, so there are no observed values to compare with. "
                "Forecasts come from the final model (trained 2006-2024). Typical error on real surveys: about 5-6 points.",
    }


def district_series(ctx, district):
    ctx.dataset.validate_location(district=district)
    d = ctx.dataset.df[ctx.dataset.df["district"] == district].sort_values("year")
    hist, _ = ctx.models.historical
    fc, _ = ctx.models.forecasts
    test_pred = hist[hist["district"] == district].set_index("year")["predicted"]
    fc_pred = fc[fc["district"] == district].set_index("year")["predicted"]
    series = []
    for _, r in d.iterrows():
        y = int(r["year"])
        series.append({"year": y,
                       "observed": clean(r[ctx.models.target]),
                       "observation_type": LABEL_SOURCE_NAMES.get(r["label_source"]),
                       "test_prediction": clean(test_pred.get(y)),
                       "forecast": clean(fc_pred.get(y))})
    return {"district": district, "province": d["province"].iloc[0], "series": series}
