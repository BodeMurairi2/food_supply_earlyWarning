"""Shared constants and helpers for the feature pipeline.

Every step produces one row per district per target year. The target year t is the
year a CFSVA survey would be collected (around April-May of year t). Features describe
the 12 months before it: April of t-1 to March of t, which covers Season B and Season C
of t-1 and Season A of t (harvested in January-February of t).
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
FEATURES = DATA / "features"
DOCS = ROOT / "documentation" / "pipeline"

FIRST_YEAR = 2006
LAST_TARGET_YEAR = 2024
LAST_YEAR = 2026  # rows for 2025-2026 carry features only (forecast rows)
YEARS = list(range(FIRST_YEAR, LAST_YEAR + 1))

# NISR district codes: province digit + district number (RW11 = Nyarugenge).
# Province names follow the NISR gazetteer used by the rainfall data.
DISTRICTS = pd.DataFrame(
    [
        ("RW11", "Nyarugenge", "Kigali City"), ("RW12", "Gasabo", "Kigali City"), ("RW13", "Kicukiro", "Kigali City"),
        ("RW21", "Nyanza", "Southern Province"), ("RW22", "Gisagara", "Southern Province"), ("RW23", "Nyaruguru", "Southern Province"),
        ("RW24", "Huye", "Southern Province"), ("RW25", "Nyamagabe", "Southern Province"), ("RW26", "Ruhango", "Southern Province"),
        ("RW27", "Muhanga", "Southern Province"), ("RW28", "Kamonyi", "Southern Province"),
        ("RW31", "Karongi", "Western Province"), ("RW32", "Rutsiro", "Western Province"), ("RW33", "Rubavu", "Western Province"),
        ("RW34", "Nyabihu", "Western Province"), ("RW35", "Ngororero", "Western Province"), ("RW36", "Rusizi", "Western Province"),
        ("RW37", "Nyamasheke", "Western Province"),
        ("RW41", "Rulindo", "Northern Province"), ("RW42", "Gakenke", "Northern Province"), ("RW43", "Musanze", "Northern Province"),
        ("RW44", "Burera", "Northern Province"), ("RW45", "Gicumbi", "Northern Province"),
        ("RW51", "Rwamagana", "Eastern Province"), ("RW52", "Nyagatare", "Eastern Province"), ("RW53", "Gatsibo", "Eastern Province"),
        ("RW54", "Kayonza", "Eastern Province"), ("RW55", "Kirehe", "Eastern Province"), ("RW56", "Ngoma", "Eastern Province"),
        ("RW57", "Bugesera", "Eastern Province"),
    ],
    columns=["district_pcode", "district", "province"],
)
DISTRICT_NAMES = set(DISTRICTS["district"])


def district_from_code(province_digit, district_number):
    """Map NISR province digit + district number (e.g. 5, 7) to a district name."""
    match = DISTRICTS[DISTRICTS["district_pcode"] == f"RW{int(province_digit)}{int(district_number)}"]
    return match["district"].iloc[0] if len(match) else None


def clean_district(value):
    """Normalise a district label such as '11 Nyarugenge', 'NYARUGENGE ' or 'Nyarugenge District'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = "".join(ch for ch in str(value) if ch.isalpha() or ch == " ").replace("District", "").strip().title()
    return text if text in DISTRICT_NAMES else None


def panel():
    """Empty district x year frame that every step's output is aligned to."""
    years = pd.DataFrame({"year": YEARS})
    return DISTRICTS.merge(years, how="cross")[["year", "province", "district", "district_pcode"]]


def window_months(year):
    """Monthly periods of the feature window for target year t: April t-1 to March t."""
    return pd.period_range(f"{year - 1}-04", f"{year}-03", freq="M")


def save(df, name):
    """Save a step's output table to data/features/<name>, print its size and return the path."""
    FEATURES.mkdir(parents=True, exist_ok=True)
    path = FEATURES / name
    df.to_csv(path, index=False)
    print(f"Wrote {path.relative_to(ROOT)}: {len(df)} rows, {df.shape[1]} columns")
    return path
