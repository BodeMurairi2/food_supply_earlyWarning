from pathlib import Path

import cdsapi

dataset = "satellite-land-surface-temperature"
request = {
    "variable": ["land_surface_temperature"],
    "month": [
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12"
    ],
    "version": ["v3_00"],
    "area": [-1, 28.8, -2.9, 31]
}

# CDS charges 1 unit per month per observation time, with a limit of 13 per request
# (the area crop does not reduce the cost), so request one year and one observation time at a time.
out_dir = Path("data/land_surface_temperature")
out_dir.mkdir(parents=True, exist_ok=True)

client = cdsapi.Client()
for year in range(1995, 2026):
    for observation_time in ["day", "night"]:
        target = out_dir / f"lst_{year}_{observation_time}.zip"
        if target.exists():
            print(f"Skipping {year} {observation_time}, already downloaded")
            continue
        client.retrieve(
            dataset,
            {**request, "year": [str(year)], "observation_time": [observation_time]},
        ).download(str(target))
