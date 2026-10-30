"""Historical analysis: 2021-2024 predictions against observed values."""

from api.data.serialization import records
from api.model.metrics import scores


def historical_table(ctx, province=None, district=None, year=None):
    ctx.dataset.validate_location(province, district)
    rows, _ = ctx.models.historical
    rows = ctx.dataset.filter_locations(rows, province, district)
    if year:
        rows = rows[rows["year"] == year]
    cols = ["year", "province", "district", "observed", "observation_type", "is_real_survey", "predicted",
            "error", "observed_risk", "predicted_risk", "persistence"]
    rows = rows.sort_values(["year", "province", "district"])
    survey = rows[rows["is_real_survey"]]
    return {
        "rows": records(rows[cols]),
        "metrics": {
            "all_rows": scores(rows["observed"], rows["predicted"]),
            "real_surveys": scores(survey["observed"], survey["predicted"]),
            "persistence_real_surveys": scores(survey["observed"], survey["persistence"]),
        },
    }
