"""
Public-holiday lookups for POD (destination) countries using python-holidays.
"""

from __future__ import annotations

from datetime import date

import holidays

# Labels must match `POD Country` values in data/TT_Offset.csv
POD_COUNTRY_TO_ISO2: dict[str, str] = {
    "Lithuania": "LT",
    "Romania": "RO",
    "Spain": "ES",
    "Germany": "DE",
}


def _holiday_name(cal: holidays.HolidayBase, d: date) -> str | None:
    name = cal.get(d)
    if name is None:
        return None
    if isinstance(name, list):
        return name[0] if name else "Public holiday"
    return str(name)


def pod_public_holiday_on_date(pod_country: str, d: date) -> str | None:
    """
    If `d` is a public holiday in the POD country, return the holiday name; else None.

    Unknown POD labels (not in POD_COUNTRY_TO_ISO2) return None (no flag).
    """
    key = pod_country.strip()
    iso = POD_COUNTRY_TO_ISO2.get(key)
    if not iso:
        return None
    cal = holidays.country_holidays(iso, years=d.year)
    return _holiday_name(cal, d)
