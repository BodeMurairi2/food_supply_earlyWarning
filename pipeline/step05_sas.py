"""Step 5 - Agricultural features from the NISR Seasonal Agricultural Survey (SAS).

Source: plot-level SAS microdata in data/sas/<year>/ (Stata files).
- 2017-2025: full features (this file).
- 2013-2016: older questionnaire layout, read by sas_legacy.py. These rounds have no
  harvest quantities per district, so they add crop area, improved seed, inorganic
  fertilizer use and % sold, but no production or yield. 2013 Season A is skipped
  (its IDs do not identify districts).

Column names change between years, so every variable is found by its question label
(e.g. "Total quantity of harvest ... (in Kg)") rather than its name. What was found
for each year and season is written to data/features/05_sas_variables_found.csv.

For target year t the window is Season B and Season C of t-1 plus Season A of t,
i.e. the harvests in the 12 months before a CFSVA survey.

Outputs:
    data/features/05_sas_district_season.csv   one row per district per survey season
    data/features/05_sas.csv                    one row per district per target year
"""

import re
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

import sas_legacy
from common import DATA, clean_district, district_from_code, panel, save

YEARS = range(2017, 2026)
CROPS = {
    "maize": r"maize",
    "beans": r"(?<!soy)bean",
    "cassava": r"cassava",
    "irish_potato": r"irish potato",
    "sweet_potato": r"sweet potato",
    "sorghum": r"sorghum",
    "banana": r"banana",
    "rice": r"rice|paddy",
}
FERT_TYPES = {"dap": r"dap", "urea": r"urea", "npk": r"npk"}
UNIT_TO_KG = {r"^\s*kg|kilo": 1.0, r"^\s*g\b|gram": 0.001}


def find(labels, pattern, exclude=None):
    for col, lab in labels.items():
        text = f"{col} {lab or ''}"
        if re.search(pattern, text, re.I) and not (exclude and re.search(exclude, text, re.I)):
            return col
    return None


def season_of(path):
    m = re.search(r"season[\s_-]*([abc])|([ABC])20\d\d", path, re.I)
    return (m.group(1) or m.group(2)).upper() if m else None


def sas_files():
    rows = []
    for year in YEARS:
        for f in sorted((DATA / "sas" / str(year)).rglob("*.dta")):
            name = f.name.lower()
            if "lsf" in name:  # 2017-2018 keep large farms in separate files; use small farms only
                continue
            kind = "production" if "produc" in name else "fertilizer" if "fertil" in name else None
            if kind:
                rows.append((year, season_of(str(f.relative_to(DATA))), kind, f))
    df = pd.DataFrame(rows, columns=["year", "season", "kind", "path"]).drop_duplicates(["year", "season", "kind"])
    return df


def read(path):
    d, meta = pyreadstat.read_dta(path, apply_value_formats=False)
    return d, meta.column_names_to_labels, meta.variable_value_labels


def _code(v):
    """Codes are sometimes stored as text ('8'); turn them back into numbers for label lookup."""
    try:
        f = float(v)
        return int(f) if f.is_integer() else f
    except (TypeError, ValueError):
        return v


def decode(d, vlabels, col, fallback_labels=None):
    """Value labels of a coded column as lowercase text."""
    if col is None:
        return pd.Series("", index=d.index)
    mapping = vlabels.get(col) or fallback_labels or {}
    return d[col].map(lambda v: str(mapping.get(_code(v), v))).str.lower()


def yes_no(text):
    return np.where(text.str.match(r"^(yes|1(\.0)?$)"), 1.0, np.where(text.isin(["", "nan", "none"]), np.nan, 0.0))


def district_column(d, vlabels):
    raw = d["s1q2"]
    labels = vlabels.get("s1q2", {})
    names = raw.map(lambda v: clean_district(labels.get(_code(v), v)))
    if names.isna().mean() > 0.5:  # unlabelled numeric codes such as 57 -> Bugesera
        codes = pd.to_numeric(raw, errors="coerce")
        names = codes.map(lambda v: district_from_code(int(v) // 10, int(v) % 10) if pd.notna(v) and 11 <= v <= 57 else None)
    return names


def weight_column(labels):
    for name in ["finalplot_weight", "plot_weight", "Plot_weight", "weight_plot", "weight"]:
        if name in labels:
            return name
    return None


def to_ha(series, label):
    """Area in hectares. Unit from the label when it says so, otherwise from the size of the values."""
    values = pd.to_numeric(series, errors="coerce")
    label = label or ""
    if re.search(r"square|sqm|m2", label, re.I):
        return values / 10_000
    if re.search(r"\bha\b|hectare", label, re.I):
        return values
    return values / 10_000 if values.median() >= 10 else values


CROP_LABELS = {}  # year -> crop value labels, reused when a season's file has none


def production_season(path, year):
    d, labels, vlabels = read(path)
    found = {
        "crop": find(labels, r"crop[ _.]*(name|code)", exclude=r"_o\b|specify|other|categor"),
        "harvest_kg": find(labels, r"total quantity of harvest"),
        "harv_area": find(labels, r"harvested crop area|harv(ested)?_area"),
        "crop_area": find(labels, r"crop area in square meters"),
        "dev_area": find(labels, r"developped crop area"),
        "plot_area": "s2q2" if "s2q2" in labels else None,
        "proportion": find(labels, r"crop proportion \(in %\)"),
        "n_crops": find(labels, r"number of main crops"),
        "seed_type": find(labels, r"types? of seeds? sown"),
        "sold_kg": find(labels, r"(quantity|qty).{0,40}sold", exclude=r"have you|price|market"),
        "all_plots_kg": find(labels, r"produced in all plots|total qty of produced"),
        "compare": find(labels, r"compare (the )?(harvest|production)", exclude=r"explanation"),
        "weight": weight_column(labels),
    }
    if found["crop"] and vlabels.get(found["crop"]):
        CROP_LABELS.setdefault(year, vlabels[found["crop"]])
    out = pd.DataFrame({"district": district_column(d, vlabels)})
    out["w"] = pd.to_numeric(d[found["weight"]], errors="coerce") if found["weight"] else 1.0
    crop = decode(d, vlabels, found["crop"], CROP_LABELS.get(year))
    out["crop"] = None
    for key, pat in CROPS.items():
        out.loc[out["crop"].isna() & crop.str.contains(pat, regex=True), "crop"] = key
    out["harvest_kg"] = pd.to_numeric(d[found["harvest_kg"]], errors="coerce") if found["harvest_kg"] else np.nan

    # Crop area, best available definition first (see 05_sas_variables_found.csv: area_source).
    plot_ha = to_ha(d[found["plot_area"]], labels[found["plot_area"]]) if found["plot_area"] else pd.Series(np.nan, index=d.index)
    area, source = pd.Series(np.nan, index=d.index), None
    if found["harv_area"]:
        area, source = to_ha(d[found["harv_area"]], labels[found["harv_area"]]), "harvested_area"
    elif found["crop_area"]:
        area, source = to_ha(d[found["crop_area"]], labels[found["crop_area"]]), "crop_area"
    elif found["dev_area"] and pd.to_numeric(d[found["dev_area"]], errors="coerce").median() < 0.8 * plot_ha.median():
        area, source = to_ha(d[found["dev_area"]], labels[found["dev_area"]]), "developed_crop_area"
    elif found["proportion"]:
        area, source = plot_ha * pd.to_numeric(d[found["proportion"]], errors="coerce") / 100, "plot_x_proportion"
    elif found["n_crops"]:
        area, source = plot_ha / pd.to_numeric(d[found["n_crops"]], errors="coerce").clip(lower=1), "plot_div_n_crops"
    found["area_source"] = source
    out["area_ha"] = area.where(area > 0)

    seed = decode(d, vlabels, found["seed_type"])
    out["improved_seed"] = np.where(seed.str.contains(r"improv|both|1&2"), 1.0, np.where(seed.str.contains(r"trad|local"), 0.0, np.nan))
    # "Quantity sold" is reported per crop for all of the farmer's plots, while harvest is per plot.
    # Use the share sold of the all-plots production when available, capped at 100%, applied to
    # this plot's harvest.
    if found["sold_kg"]:
        sold = pd.to_numeric(d[found["sold_kg"]], errors="coerce")
        denom = pd.to_numeric(d[found["all_plots_kg"]], errors="coerce") if found["all_plots_kg"] else out["harvest_kg"]
        out["sold_share"] = (sold / denom.where(denom > 0)).clip(0, 1)
        out["sold_kg"] = out["sold_share"] * out["harvest_kg"]
    else:
        out["sold_kg"] = np.nan
        out["sold_share"] = np.nan
    comp = decode(d, vlabels, found["compare"])
    out["worse_harvest"] = np.where(comp.str.contains(r"less|decreas|lower|worse|reduc"), 1.0, np.where(comp.str.strip().isin(["", "nan"]), np.nan, 0.0))
    return out[out["district"].notna()], found


def fertilizer_season(path):
    d, labels, vlabels = read(path)
    cols = list(labels)
    used = find(labels, r"inorganic fertil\w* in this plot") or ("s3q9" if "s3q9" in labels else None)
    groups, current = [], None
    for c in cols:
        lab = (labels[c] or "").lower()
        if "pestic" in lab or "fungic" in lab:
            current = None
            continue
        if re.search(r"type of inorganic|inorganic fertil\w*\s+\(?type", lab) and not re.search(r"_o(ther)?_?\d*$", c, re.I):
            current = {"type": c, "unit": None, "qty": None}
            groups.append(current)
        elif current is not None and current["unit"] is None and re.search(r"unit", lab) and "price" not in lab:
            current["unit"] = c
        elif current is not None and current["qty"] is None and re.search(r"total quantity", lab):
            current["qty"] = c
    if not groups and {"s3q10", "s3q11", "s3q12"} <= set(cols):  # unlabelled file (2022 Season C)
        groups = [{"type": "s3q10", "unit": "s3q11", "qty": "s3q12"}]
    weight = weight_column(labels)
    out = pd.DataFrame({"district": district_column(d, vlabels)})
    out["w"] = pd.to_numeric(d[weight], errors="coerce") if weight else 1.0
    out["plot_ha"] = to_ha(d["s2q2"], labels.get("s2q2")) if "s2q2" in d else np.nan
    out["inorganic_used"] = yes_no(decode(d, vlabels, used))
    for k in FERT_TYPES:
        out[f"{k}_kg"] = 0.0
    out["inorganic_kg"] = 0.0
    for g in groups:
        if not g["qty"]:
            continue
        ftype = decode(d, vlabels, g["type"])
        unit = decode(d, vlabels, g["unit"]) if g["unit"] else pd.Series("kg", index=d.index)
        factor = pd.Series(np.nan, index=d.index)
        for pat, f in UNIT_TO_KG.items():
            factor = factor.where(~(factor.isna() & unit.str.contains(pat, regex=True)), f)
        factor = factor.where(~(factor.isna() & unit.isin(["1", "1.0"])), 1.0)  # unit code 1 = kg
        kg = (pd.to_numeric(d[g["qty"]], errors="coerce") * factor).fillna(0)
        out["inorganic_kg"] += kg
        for k, pat in FERT_TYPES.items():
            out[f"{k}_kg"] += kg.where(ftype.str.contains(pat, regex=True), 0)
    if not any(g["qty"] for g in groups):
        out[["inorganic_kg"] + [f"{k}_kg" for k in FERT_TYPES]] = np.nan
    # Long-format years repeat a plot once per fertilizer type: keep plot area once.
    plot_id = [c for c in ["Segment_ID", "s1q0", "s1q4", "s1q6", "s2q1"] if c in d]
    out["plot_key"] = d[plot_id].map(str).agg("|".join, axis=1) if plot_id else d.index.astype(str)
    found = {"inorganic_used": used, "fert_groups": len([g for g in groups if g["qty"]]), "weight": weight}
    return out[out["district"].notna()], found


def summarise_production(p):
    rows = []
    for district, g in p.groupby("district"):
        r = {"district": district}
        for crop in CROPS:
            c = g[(g["crop"] == crop) & g["harvest_kg"].notna() & g["area_ha"].notna()]
            r[f"{crop}_kg"] = (c["harvest_kg"] * c["w"]).sum()
            r[f"{crop}_ha"] = (c["area_ha"] * c["w"]).sum()
        s = g[g["improved_seed"].notna()]
        r["seed_w"], r["improved_w"] = s["w"].sum(), (s["improved_seed"] * s["w"]).sum()
        s = g[g["sold_share"].notna()]
        # Same definition as 2013-2016: average % sold per crop record (unweighted by quantity).
        r["sold_pct_sum"], r["sold_pct_n"] = 100 * s["sold_share"].sum(), len(s)
        s = g[g["worse_harvest"].notna()]
        r["compare_w"], r["worse_w"] = s["w"].sum(), (s["worse_harvest"] * s["w"]).sum()
        rows.append(r)
    return pd.DataFrame(rows)


def summarise_fertilizer(f):
    plots = f.groupby(["district", "plot_key"]).agg(
        w=("w", "first"), plot_ha=("plot_ha", "first"), inorganic_used=("inorganic_used", "max"),
        inorganic_kg=("inorganic_kg", "sum"), dap_kg=("dap_kg", "sum"), urea_kg=("urea_kg", "sum"), npk_kg=("npk_kg", "sum"),
    ).reset_index()
    plots = plots[plots["plot_ha"] > 0]
    agg = {"plots_w": ("w", "sum")}
    out = plots.assign(
        fert_area_w=plots["plot_ha"] * plots["w"],
        used_w=plots["inorganic_used"].fillna(0) * plots["w"],
        **{f"{k}_w": plots[k] * plots["w"] for k in ["inorganic_kg", "dap_kg", "urea_kg", "npk_kg"]},
    ).groupby("district")[["w", "fert_area_w", "used_w", "inorganic_kg_w", "dap_kg_w", "urea_kg_w", "npk_kg_w"]].sum().reset_index()
    return out.rename(columns={"w": "plots_w"})


def main():
    files = sas_files()
    seasons, found_log = [], []
    files["order"] = files["season"].map({"A": 0, "B": 1, "C": 2})
    for (year, _, season), g in files.sort_values(["year", "order"]).groupby(["year", "order", "season"]):
        row = {"sas_year": year, "season": season}
        parts = []
        for _, f in g.iterrows():
            if f["kind"] == "production":
                p, found = production_season(f["path"], year)
                parts.append(summarise_production(p))
            else:
                fe, found = fertilizer_season(f["path"])
                parts.append(summarise_fertilizer(fe))
            found_log.append({"sas_year": year, "season": season, "kind": f["kind"], "file": str(Path(f["path"]).relative_to(DATA)), **found})
        merged = parts[0]
        for extra in parts[1:]:
            merged = merged.merge(extra, on="district", how="outer")
        seasons.append(merged.assign(sas_year=year, season=season))
        print(f"SAS {year} {season}: {merged['district'].nunique()} districts")
    legacy, legacy_log = sas_legacy.legacy_seasons(CROPS)
    seasons = pd.concat(seasons + [legacy], ignore_index=True)
    found_log += legacy_log
    save(pd.DataFrame(found_log), "05_sas_variables_found.csv")

    # Season -> target year: B and C of t-1, A of t.
    seasons["year"] = np.where(seasons["season"] == "A", seasons["sas_year"], seasons["sas_year"] + 1)
    save(seasons.sort_values(["sas_year", "season", "district"]).round(3), "05_sas_district_season.csv")

    sums = seasons.drop(columns=["sas_year", "season"]).groupby(["district", "year"]).sum(min_count=1)
    n_seasons = seasons.groupby(["district", "year"]).size().rename("sas_n_seasons")
    # Legacy area comes from weighted screening files, so those years count as weighted.
    weighted_years = {r["sas_year"] for r in found_log if (r["kind"] == "production" and r["weight"]) or r["kind"] == "legacy"}
    feats = pd.DataFrame(index=sums.index)
    for crop in CROPS:
        feats[f"sas_{crop}_yield_kg_ha"] = sums[f"{crop}_kg"] / sums[f"{crop}_ha"].replace(0, np.nan)
        feats[f"sas_{crop}_production_t"] = sums[f"{crop}_kg"] / 1000
        feats[f"sas_{crop}_area_ha"] = sums[f"{crop}_ha"].add(sums.get(f"{crop}_area_only_ha"), fill_value=0) if f"{crop}_area_only_ha" in sums else sums[f"{crop}_ha"]
    feats["sas_improved_seed_pct"] = 100 * sums["improved_w"] / sums["seed_w"].replace(0, np.nan)
    # Average % of harvest sold per crop record, the same definition for all years.
    feats["sas_sold_pct"] = sums["sold_pct_sum"] / sums["sold_pct_n"].replace(0, np.nan)
    feats["sas_worse_harvest_pct"] = 100 * sums["worse_w"] / sums["compare_w"].replace(0, np.nan)
    feats["sas_inorganic_fert_plots_pct"] = 100 * sums["used_w"] / sums["plots_w"].replace(0, np.nan)
    for k in ["inorganic", "dap", "urea", "npk"]:
        feats[f"sas_{k}_kg_ha"] = sums[f"{k}_kg_w"] / sums["fert_area_w"].replace(0, np.nan)
    feats = feats.join(n_seasons).reset_index()

    # Production and area totals need survey weights to be comparable; blank them where the
    # contributing SAS years had no weights. Yields and percentages are ratios and are kept.
    contributing = seasons.groupby(["district", "year"])["sas_year"].agg(set).reset_index()
    feats = feats.merge(contributing, on=["district", "year"])
    unweighted = ~feats["sas_year"].map(lambda ys: ys <= weighted_years)
    for c in [c for c in feats.columns if c.endswith(("_production_t", "_area_ha"))]:
        feats.loc[unweighted, c] = np.nan
    feats = feats.drop(columns="sas_year")
    feats = feats.replace([np.inf, -np.inf], np.nan)

    # Year-on-year change in yield (a drop is an early warning signal).
    feats = feats.sort_values("year")
    for crop in ["maize", "beans", "cassava", "irish_potato"]:
        prev = feats.groupby("district")[f"sas_{crop}_yield_kg_ha"].shift(1)
        prev_year = feats.groupby("district")["year"].shift(1)
        feats[f"sas_{crop}_yield_change_pct"] = (100 * (feats[f"sas_{crop}_yield_kg_ha"] / prev - 1)).where(prev_year == feats["year"] - 1)

    out = panel().merge(feats, on=["district", "year"], how="left").sort_values(["year", "district_pcode"]).round(2)
    cols = [c for c in out.columns if c.startswith("sas_")]
    print("non-missing rows per year:", out.groupby("year")["sas_n_seasons"].count().to_dict())
    print("missing values per feature:", out[cols].isna().sum().to_dict())
    save(out, "05_sas.csv")


if __name__ == "__main__":
    main()
