"""Compare ERA5-Land monthly mean temperature with NISR / Meteo Rwanda station data for 2024.

Station values come from the NISR Rwanda Statistical Yearbook 2025, tables 5.11 and 5.12
(monthly maximum and minimum temperature at 14 stations), saved in
data/nisr/station_temperature_2024.csv. Each station is compared with the ERA5-Land grid
cell that contains it. The station mean is taken as (max + min) / 2.

Outputs:
    data/processed/validation_stations_2024.csv   per station and month
    data/processed/validation_summary_2024.csv    bias / MAE / RMSE / correlation per variable
"""

import numpy as np
import pandas as pd
import xarray as xr

import process_temperature as pt

STATIONS = "data/nisr/station_temperature_2024.csv"


def at_stations(field, st):
    dates = pd.to_datetime(dict(year=st["year"], month=st["month"], day=1))
    points = field.sel(lat=xr.DataArray(st["lat"]), lon=xr.DataArray(st["lon"]), method="nearest")
    return points.sel(time=xr.DataArray(dates)).values


def main():
    st = pd.read_csv(STATIONS)
    st["station_mean_c"] = (st["tmax_c"] + st["tmin_c"]) / 2
    pairs = {"mean": ("station_mean_c", pt.load_monthly_mean())}

    summary = []
    for name, (station_col, field) in pairs.items():
        era5_col = f"era5_{name}_c"
        st[era5_col] = at_stations(field, st)
        diff = st[era5_col] - st[station_col]
        summary.append({
            "variable": name,
            "bias_c": diff.mean(),
            "mae_c": diff.abs().mean(),
            "rmse_c": np.sqrt((diff ** 2).mean()),
            "corr_all": st[station_col].corr(st[era5_col]),
            "corr_station_means": st.groupby("station")[[station_col, era5_col]].mean().corr().iloc[0, 1],
            "n": int(diff.notna().sum()),
        })

    pt.OUT_DIR.mkdir(parents=True, exist_ok=True)
    st.round(2).to_csv(pt.OUT_DIR / "validation_stations_2024.csv", index=False)
    summary = pd.DataFrame(summary).round(2)
    summary.to_csv(pt.OUT_DIR / "validation_summary_2024.csv", index=False)
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
