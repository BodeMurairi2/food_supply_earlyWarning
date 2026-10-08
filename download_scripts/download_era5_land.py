"""Download ERA5-Land monthly mean 2 m air temperature over Rwanda from the Copernicus CDS.

- 1995 up to last year: the monthly means product, in a single request.
- Current year: the CDS restricts monthly means of the newest, preliminary data
  (ERA5-LandT), so we download hourly values for the complete months available and
  average them per month in pipeline/process_temperature.py. The monthly means product is itself
  an average of all hours, so the two are consistent.

Files that already exist are skipped, so the script is safe to re-run, e.g. later in
the year to add new months.
"""

import calendar
import os
from pathlib import Path

from ecmwf.datastores import Client

START_YEAR = 1995
END_YEAR = 2026
# North, West, South, East: a box around Rwanda with a small margin.
AREA = [-1, 28.8, -2.9, 31]
# The hourly dataset allows a cost of 12,000 per request; one month costs ~1,500.
MONTHS_PER_HOURLY_REQUEST = 6

ROOT = Path(__file__).resolve().parent.parent  # repository root, so the script runs from any folder
MONTHLY_DIR = ROOT / "data" / "era5_land" / "monthly"
HOURLY_DIR = ROOT / "data" / "era5_land" / "hourly"


def make_client():
    """Create a CDS API client using the url and key saved in ~/.cdsapirc."""
    # Reuse the credentials from ~/.cdsapirc.
    config = {}
    with open(os.path.expanduser("~/.cdsapirc")) as f:
        for line in f:
            if ":" in line:
                k, v = line.split(":", 1)
                config[k.strip()] = v.strip()
    return Client(url=config["url"], key=config["key"])


def complete_months(client, year):
    """Months of `year` for which the hourly dataset already has every day."""
    process = client.get_process("reanalysis-era5-land")
    base = {"variable": ["2m_temperature"], "year": [str(year)]}
    months = []
    for month in process.apply_constraints(base)["month"]:
        days = process.apply_constraints({**base, "month": [month]})["day"]
        if len(days) == calendar.monthrange(year, int(month))[1]:
            months.append(month)
    return months


def monthly_request(years):
    """Build the CDS request for ERA5-Land monthly mean temperature over Rwanda for `years`."""
    return {
        "product_type": ["monthly_averaged_reanalysis"],
        "variable": ["2m_temperature"],
        "year": [str(y) for y in years],
        "month": [f"{m:02d}" for m in range(1, 13)],
        "time": ["00:00"],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": AREA,
    }


def hourly_request(year, months):
    """Build the CDS request for hourly ERA5-Land temperature for the given months of one year."""
    return {
        "variable": ["2m_temperature"],
        "year": [str(year)],
        "month": months,
        "day": [f"{d:02d}" for d in range(1, 32)],
        "time": [f"{h:02d}:00" for h in range(24)],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": AREA,
    }


def main():
    """Download the monthly means for 1995 to last year and the hourly files for this year."""
    MONTHLY_DIR.mkdir(parents=True, exist_ok=True)
    HOURLY_DIR.mkdir(parents=True, exist_ok=True)
    client = make_client()

    jobs = [(
        "reanalysis-era5-land-monthly-means",
        monthly_request(range(START_YEAR, END_YEAR)),
        MONTHLY_DIR / f"t2m_monthly_mean_{START_YEAR}_{END_YEAR - 1}.nc",
    )]
    months = complete_months(client, END_YEAR)
    for i in range(0, len(months), MONTHS_PER_HOURLY_REQUEST):
        chunk = months[i:i + MONTHS_PER_HOURLY_REQUEST]
        target = HOURLY_DIR / f"t2m_hourly_{END_YEAR}_{chunk[0]}-{chunk[-1]}.nc"
        jobs.append(("reanalysis-era5-land", hourly_request(END_YEAR, chunk), target))

    for dataset, request, target in jobs:
        if target.exists():
            print(f"Skipping {target.name}, already downloaded")
            continue
        print(f"Requesting {target.name}")
        client.retrieve(dataset, request, str(target))
        print(f"Downloaded {target}")


if __name__ == "__main__":
    main()
