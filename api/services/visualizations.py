"""Visualizations: climate, harvest and price trends by province and district."""

import numpy as np
import pandas as pd

from api import config
from api.data.serialization import clean


def _viz_info(variable):
    if variable not in config.VIZ_VARIABLES:
        raise ValueError(f"Unknown variable: {variable}")
    label, topic, unit, aggregation, change = config.VIZ_VARIABLES[variable]
    return {"key": variable, "label": label, "topic": topic, "unit": unit,
            "aggregation": aggregation, "change": change}


def _combine(df, column, aggregation, by):
    """Yearly value per group: sum for production, simple average otherwise. All-missing stays missing."""
    g = df.groupby(by)[column]
    return g.sum(min_count=1) if aggregation == "sum" else g.mean()


def _partial_years(variable):
    return config.SAS_PARTIAL_YEARS if variable.startswith("sas_") else {}


def viz_variables(ctx):
    items = []
    for key in config.VIZ_VARIABLES:
        info = _viz_info(key)
        years = ctx.dataset.df.loc[ctx.dataset.df[key].notna(), "year"].unique()
        info["years"] = sorted(int(y) for y in years)
        info["partial_years"] = sorted(_partial_years(key))
        items.append(info)
    return {
        "variables": items,
        "topics": list(dict.fromkeys(v["topic"] for v in items)),
        "years": [int(ctx.dataset.df["year"].min()), int(ctx.dataset.df["year"].max())],
        "default_years": [config.TEST_YEARS[0], config.FORECAST_YEARS[1]],
        "note": "Each year covers April of the year before to March of that year (the 12 months before the "
                "April-May CFSVA survey). Harvests in year t are Seasons B and C of t-1 and Season A of t.",
    }


def viz_trends(ctx, variable, level="province", province=None, district=None, start_year=2021, end_year=2026):
    info = _viz_info(variable)
    if start_year > end_year:
        raise ValueError("Start year must not be after end year")
    ctx.dataset.validate_location(province, district)
    agg = info["aggregation"]
    d = ctx.dataset.df[ctx.dataset.df["year"].between(start_year, end_year)]
    partial = {y: n for y, n in _partial_years(variable).items() if start_year <= y <= end_year}

    national = _combine(d, variable, agg, "year")
    if level == "province":
        groups, by = d, "province"
    else:
        groups, by = ctx.dataset.filter_locations(d, province), "district"
    values = _combine(groups, variable, agg, [by, "year"])
    owner = groups.drop_duplicates(by).set_index(by, drop=False)["province"]

    series = []
    for name in sorted(values.index.get_level_values(0).unique()):
        s = values.loc[name]
        series.append({"name": name, "province": owner[name],
                       "points": [{"year": int(y), "value": clean(v)} for y, v in s.items()]})

    # Ranking over complete years only, so a partial harvest year does not look like a collapse.
    complete = [int(y) for y, v in national.items() if pd.notna(v) and int(y) not in partial]
    comparison = []
    if complete:
        first, last = complete[0], complete[-1]
        for s in series:
            pts = {p["year"]: p["value"] for p in s["points"]}
            vals = [pts[y] for y in complete if pts.get(y) is not None]
            a, b = pts.get(first), pts.get(last)
            if a is None or b is None or first == last:
                change = None
            elif info["change"] == "pct":
                change = clean((b - a) / a * 100) if a else None
            else:
                change = clean(b - a)
            comparison.append({"name": s["name"], "province": s["province"],
                               "mean": clean(np.mean(vals)) if vals else None,
                               "start": a, "end": b, "change": change})

    notes = []
    if agg == "sum":
        notes.append("Province and national values are sums of district totals.")
    else:
        notes.append("Province and national values are simple averages of district values.")
    notes += list(partial.values())
    missing = int(d[variable].isna().sum())
    if missing:
        notes.append(f"{missing} of {len(d)} district-years in this range have no value for this variable.")
    if not complete:
        notes.append("No data for this variable in the selected years.")

    return {
        "variable": info,
        "level": level,
        "filters": {"province": province, "district": district, "start_year": start_year, "end_year": end_year},
        "highlight": district if level == "district" else province,
        "years": list(range(start_year, end_year + 1)),
        "series": series,
        "national": [{"year": int(y), "value": clean(v)} for y, v in national.items()],
        "comparison": {"from_year": complete[0] if complete else None,
                       "to_year": complete[-1] if complete else None,
                       "change_kind": info["change"], "rows": comparison},
        "partial_years": sorted(partial),
        "notes": notes,
    }


def viz_profile(ctx, province=None, district=None, start_year=2021, end_year=2026):
    """Rain, temperature and staple production for one area, each kept in its own units."""
    if start_year > end_year:
        raise ValueError("Start year must not be after end year")
    ctx.dataset.validate_location(province, district)
    d = ctx.dataset.filter_locations(ctx.dataset.df[ctx.dataset.df["year"].between(start_year, end_year)], province, district)
    area = district or province or "Rwanda"
    rows = []
    for y, g in d.groupby("year"):
        row = {"year": int(y),
               "rain_12m_mm": clean(g["rain_12m_mm"].mean()),
               "rain_12m_pct_normal": clean(g["rain_12m_pct_normal"].mean()),
               "temp_12m_c": clean(g["temp_12m_c"].mean()),
               "temp_12m_anomaly_c": clean(g["temp_12m_anomaly_c"].mean())}
        for c in config.STAPLE_CROPS:
            row[f"{c}_production_t"] = clean(g[f"sas_{c}_production_t"].sum(min_count=1))
        rows.append(row)
    return {
        "area": area,
        "level": "district" if district else "province" if province else "national",
        "crops": [{"key": f"{c}_production_t", "label": config.VIZ_VARIABLES[f"sas_{c}_production_t"][0]}
                  for c in config.STAPLE_CROPS],
        "rows": rows,
        "partial_years": sorted(y for y in config.SAS_PARTIAL_YEARS if start_year <= y <= end_year),
        "notes": ["Rainfall and temperature are averages over the area's districts; production is the sum.",
                  *[n for y, n in config.SAS_PARTIAL_YEARS.items() if start_year <= y <= end_year]],
    }
