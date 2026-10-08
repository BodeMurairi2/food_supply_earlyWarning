"""Aggregate ERA5-Land 2 m temperature to monthly means per Rwandan province and district.

Inputs (from download_era5_land.py and GADM 4.1):
    data/era5_land/monthly/t2m_monthly_mean_*.nc    monthly means, 1995 to last year
    data/era5_land/hourly/t2m_hourly_*.nc           hourly values for the current year
    data/boundaries/gadm41_RWA_1.json (provinces), gadm41_RWA_2.json (districts)

Outputs:
    data/processed/temperature_monthly_province.csv
    data/processed/temperature_monthly_district.csv

Each grid cell (0.1°, ~11 km) is weighted by the fraction of it that lies inside the
region, so small districts such as those in Kigali still get a sensible value. Cells
without data, if any, are left out of the average.
"""

from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import regionmask
import xarray as xr

ERA5_DIR = Path("data/era5_land")
BOUNDARY_DIR = Path("data/boundaries")
OUT_DIR = Path("data/processed")

PROVINCE_EN = {
    "Amajyaruguru": "Northern",
    "Amajyepfo": "Southern",
    "Iburasirazuba": "Eastern",
    "Iburengerazuba": "Western",
    "UmujyiwaKigali": "Kigali City",
}


def open_t2m(path):
    """Open an ERA5-Land file and return 2 m temperature in °C with a `time` dimension."""
    ds = xr.open_dataset(path)
    ds = ds.rename({k: v for k, v in {"valid_time": "time", "latitude": "lat", "longitude": "lon"}.items() if k in ds.dims})
    t2m = ds["t2m"] - 273.15
    return t2m.drop_vars([c for c in t2m.coords if c not in ("time", "lat", "lon")])


def load_monthly_mean():
    files = sorted((ERA5_DIR / "monthly").glob("t2m_monthly_mean_*.nc"))
    if not files:
        raise SystemExit("No monthly files yet - run download_era5_land.py first")
    t2m = xr.concat([open_t2m(f) for f in files], dim="time").sortby("time")
    t2m = t2m.assign_coords(time=t2m["time"].dt.floor("D"))

    # The newest months are not available as monthly means, so average the hourly values.
    hourly_files = sorted((ERA5_DIR / "hourly").glob("t2m_hourly_*.nc"))
    if hourly_files:
        hourly = xr.concat([open_t2m(f) for f in hourly_files], dim="time").sortby("time")
        newer = hourly.resample(time="MS").mean()
        newer = newer.sel(time=newer["time"] > t2m["time"].max())
        t2m = xr.concat([t2m, newer.reindex_like(t2m.isel(time=0), method="nearest")], dim="time")
    return t2m


def region_weights(regions_gdf, name_col, grid):
    """Fraction of each grid cell inside each region, shape (region, lat, lon)."""
    regions = regionmask.from_geopandas(regions_gdf, names=name_col, overlap=False)
    frac = regions.mask_3D_frac_approx(grid["lon"], grid["lat"])
    # Cells near the equator are almost equal in area, but weight by cos(lat) anyway.
    return frac * np.cos(np.deg2rad(frac["lat"]))


def regional_mean(field, weights):
    """Weighted mean per region and month, ignoring cells with no data."""
    valid = field.notnull()
    total = (field.fillna(0) * weights).sum(("lat", "lon"))
    weight_sum = (weights * valid).sum(("lat", "lon"))
    return (total / weight_sum).where(weight_sum > 0)


def aggregate(field, regions_gdf, name_col):
    weights = region_weights(regions_gdf, name_col, field)
    df = regional_mean(field, weights).to_series().rename("temp_mean_c").reset_index()
    df["region"] = df["region"].map(dict(enumerate(regions_gdf[name_col])))
    return df.rename(columns={"time": "date"})


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    t2m = load_monthly_mean()

    provinces = gpd.read_file(BOUNDARY_DIR / "gadm41_RWA_1.json")
    districts = gpd.read_file(BOUNDARY_DIR / "gadm41_RWA_2.json")

    for level, gdf, name_col in [("province", provinces, "NAME_1"), ("district", districts, "NAME_2")]:
        df = aggregate(t2m, gdf, name_col)
        if level == "province":
            df = df.rename(columns={"region": "province_rw"})
        else:
            lookup = districts.set_index("NAME_2")["NAME_1"]
            df = df.rename(columns={"region": "district"})
            df["province_rw"] = df["district"].map(lookup)
        df["province"] = df["province_rw"].map(PROVINCE_EN)
        df["year"] = df["date"].dt.year
        df["month"] = df["date"].dt.month

        id_cols = ["date", "year", "month", "province", "province_rw"] + (["district"] if level == "district" else [])
        df = df[id_cols + ["temp_mean_c"]].sort_values(id_cols[3:] + ["date"])
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")
        out = OUT_DIR / f"temperature_monthly_{level}.csv"
        df.round(2).to_csv(out, index=False)
        print(f"Wrote {out}: {len(df)} rows, {df['date'].min()} to {df['date'].max()}")


if __name__ == "__main__":
    main()
