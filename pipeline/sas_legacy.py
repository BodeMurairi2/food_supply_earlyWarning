"""SAS 2013-2016 (older questionnaire layout) -> district sums per season.

These rounds differ from 2017+ in three ways:
- the district is not a column: it is the first two digits of the household / tract ID
  (e.g. 571124067 -> 57 = Bugesera);
- harvest uses (sold, eaten, stored...) are recorded as a percentage of the harvest, not
  in kg, and no file has the harvest quantity per district. NISR only published national
  (and for 2013 province) production, so district production and yield cannot be computed;
- fertilizer is recorded as used / not used and type, without quantities.

What can be computed per district and season: crop area (ha, survey-weighted, from the
screening files), share of crop plots with improved seed, share of plots with inorganic
fertilizer, and the average share of harvest sold.

Large-farm files (LSF, *_BIG) are skipped, as for 2017-2018.
"""

import re

import numpy as np
import pandas as pd
import pyreadstat

from common import DATA, district_from_code

YEARS = range(2013, 2017)
SKIP = r"lsf|_big|province|phys|national|yield|total"


def _season(path):
    """Return the season letter (A, B or C) found in a file path, or None."""
    m = re.search(r"season[\s_-]*([abc])\b|season[\s_-]*([abc])[^a-z]|screening_?([abc])\b|screening2016([abc])", path, re.I)
    return next(g for g in m.groups() if g).upper() if m else None


def _district(ids):
    """District = first two digits of the household / tract ID (e.g. 571124067 -> 57 = Bugesera)."""
    text = pd.to_numeric(ids, errors="coerce").dropna().astype("int64").astype(str)
    codes = text.str[:2].astype(int)
    return codes.map(lambda c: district_from_code(c // 10, c % 10)).reindex(ids.index)


def _pick(labels, names=(), pattern=None):
    """Return the first column named in `names`, else the first whose name or label matches `pattern`."""
    lower = {c.lower(): c for c in labels}
    for n in names:
        if n.lower() in lower:
            return lower[n.lower()]
    if pattern:
        for c, lab in labels.items():
            if re.search(pattern, f"{c} {lab or ''}", re.I):
                return c
    return None


def _decode(d, vlabels, col):
    """Return the value labels of column `col` as lowercase text."""
    mapping = vlabels.get(col, {})
    return d[col].map(lambda v: str(mapping.get(v, v))).str.lower()


def _files():
    """List the 2013-2016 SAS files with their year and season, skipping large-farm and national files."""
    rows = []
    for year in YEARS:
        for f in sorted((DATA / "sas" / str(year)).rglob("*.dta")):
            rel = str(f.relative_to(DATA))
            if re.search(SKIP, f.name, re.I):
                continue
            rows.append((year, _season(rel), f))
    return pd.DataFrame(rows, columns=["year", "season", "path"]).dropna()


def _read(path):
    """Read a Stata file and return the data, column labels and value labels."""
    d, meta = pyreadstat.read_dta(path, apply_value_formats=False)
    return d, meta.column_names_to_labels, meta.variable_value_labels


def area_by_crop(d, labels, vlabels, crops):
    """Return weighted crop area (ha) per district and crop from a screening file, or None."""
    crop = _pick(labels, ["crop_code"])
    area = _pick(labels, ["ha", "Area_Ha", "Area", "area_crop", "Ha_p"])
    ident = _pick(labels, ["idquest", "tractid"])
    if not (crop and area and ident):
        return None
    w = pd.to_numeric(d[_pick(labels, ["weight", "coef"])], errors="coerce") if _pick(labels, ["weight", "coef"]) else 1.0
    out = pd.DataFrame({"district": _district(d[ident]), "w": w, "ha": pd.to_numeric(d[area], errors="coerce")})
    name = _decode(d, vlabels, crop)
    out["crop"] = None
    for key, pat in crops.items():
        out.loc[out["crop"].isna() & name.str.contains(pat, regex=True), "crop"] = key
    out = out.dropna(subset=["district", "crop", "ha"])
    out["ha_w"] = out["ha"] * out["w"]
    return out.pivot_table(index="district", columns="crop", values="ha_w", aggfunc="sum").add_suffix("_area_only_ha")


def share(d, labels, vlabels, col, positive, negative):
    """Return weighted totals per district of all records and of records matching `positive`."""
    ident = _pick(labels, ["idquest", "tractid"])
    if not (col and ident):
        return None
    w = pd.to_numeric(d[_pick(labels, ["weight", "coef"])], errors="coerce") if _pick(labels, ["weight", "coef"]) else pd.Series(1.0, index=d.index)
    text = _decode(d, vlabels, col)
    flag = pd.Series(np.where(text.str.contains(positive), 1.0, np.where(text.str.contains(negative), 0.0, np.nan)), index=d.index)
    out = pd.DataFrame({"district": _district(d[ident]), "w": w, "flag": flag}).dropna()
    g = out.assign(x=out["flag"] * out["w"]).groupby("district")
    return pd.DataFrame({"n_w": g["w"].sum(), "x_w": g["x"].sum()})


def season_table(paths, crops):
    """Combine all files of one legacy season into the district-level sums used by step 5."""
    parts, found = [], {}
    for path in paths:
        d, labels, vlabels = _read(path)
        name = path.name.lower()
        if re.search(r"screen|area_season|pure_mixed|area_province_crop", name):
            a = area_by_crop(d, labels, vlabels, crops)
            if a is not None and "area" not in found:
                parts.append(a)
                found["area"] = path.name
        seed = _pick(labels, ["type_of_seeds_sown", "seeds", "Seeds"], r"types? of seeds")
        if seed and "seed" not in found and not re.search(r"improved by crop|traditional by crop", name):
            s = share(d, labels, vlabels, seed, r"improv|and", r"trad")
            if s is not None and len(s):
                parts.append(s.rename(columns={"n_w": "seed_w", "x_w": "improved_w"}))
                found["seed"] = path.name
        fert = _pick(labels, ["inorganic", "have_u_already_used_this_in"], r"used this inorganic")
        if fert and "fertilizer" not in found:
            s = share(d, labels, vlabels, fert, r"^yes|^1(?:\.0)?$", r"^no|^2(?:\.0)?$")
            if s is not None and len(s):
                parts.append(s.rename(columns={"n_w": "plots_w", "x_w": "used_w"}))
                found["fertilizer"] = path.name
        sold = _pick(labels, ["sold", "crop_proportion__the__field", "qty_sold", "C02", "C0"], r"qty sold|quantity sold")
        ident = _pick(labels, ["idquest", "tractid"])
        if sold and ident and "sold" not in found and re.search(r"part_?[45]|part_iv\b|use.?of.?produc", name):
            pct = pd.to_numeric(d[sold], errors="coerce")
            t = pd.DataFrame({"district": _district(d[ident]), "pct": pct}).dropna()
            t = t[t["pct"].between(0, 100)]
            g = t.groupby("district")["pct"]
            parts.append(pd.DataFrame({"sold_pct_sum": g.sum(), "sold_pct_n": g.size()}))
            found["sold"] = path.name
    if not parts:
        return None, found
    table = pd.concat(parts, axis=1).reset_index().rename(columns={"index": "district"})
    return table, found


def legacy_seasons(crops):
    """Build district tables for every usable 2013-2016 season and return them with a log of files used."""
    seasons, log = [], []
    files = _files()
    for (year, season), g in files.groupby(["year", "season"]):
        table, found = season_table(list(g["path"]), crops)
        log.append({"sas_year": year, "season": season, "kind": "legacy", **found})
        # In 2013 Season A the IDs encode province + stratum, not the district: the digits then
        # map to only one (wrong) district per province. Keep a season only if it covers 20+ districts.
        if table is not None and table["district"].nunique() < 20:
            print(f"SAS {year} {season} (legacy): skipped, IDs give only {table['district'].nunique()} districts")
            log[-1]["skipped"] = "IDs do not identify districts"
            continue
        if table is not None:
            seasons.append(table.assign(sas_year=year, season=season))
            print(f"SAS {year} {season} (legacy): {table['district'].nunique()} districts, files used: {found}")
    return pd.concat(seasons, ignore_index=True), log
