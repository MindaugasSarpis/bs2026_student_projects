"""
Load product/supplier and transit-time tables from CSV and merge by POL + POD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

_DATA_DIR = Path(__file__).resolve().parent / "data"


def _products_path() -> Path:
    return _DATA_DIR / "Products_Suppliers.csv"


def _tt_offset_path() -> Path:
    return _DATA_DIR / "TT_Offset.csv"


def load_products() -> pd.DataFrame:
    df = pd.read_csv(_products_path())
    df["POL_Country"] = df["POL_Country"].astype(str).str.strip()
    return df


def load_tt_matrix() -> pd.DataFrame:
    df = pd.read_csv(_tt_offset_path())
    df = df.rename(
        columns={
            "POL Country": "pol_country",
            "POD Country": "pod_country",
            "TT": "tt_days",
            "POD offset": "pod_offset_days",
        }
    )
    df["pol_country"] = df["pol_country"].astype(str).str.strip()
    df["pod_country"] = df["pod_country"].astype(str).str.strip()
    df["tt_days"] = pd.to_numeric(df["tt_days"], errors="coerce")
    df["pod_offset_days"] = pd.to_numeric(df["pod_offset_days"], errors="coerce")
    return df


def distinct_pod_countries(tt: pd.DataFrame | None = None) -> list[str]:
    if tt is None:
        tt = load_tt_matrix()
    pods = sorted(tt["pod_country"].dropna().unique().tolist())
    return pods


def merge_product_transit(
    product_row: pd.Series,
    pod: str,
    tt: pd.DataFrame | None = None,
) -> dict[str, Any] | None:
    """
    Match product POL_Country to TT matrix for the given POD.

    Returns a flat dict for display, or None if no lane exists.
    """
    if tt is None:
        tt = load_tt_matrix()
    pol = str(product_row.get("POL_Country", "")).strip()
    pod_s = str(pod).strip()
    hit = tt[(tt["pol_country"] == pol) & (tt["pod_country"] == pod_s)]
    if hit.empty:
        return None
    row = hit.iloc[0]
    tt_val = int(row["tt_days"]) if pd.notna(row["tt_days"]) else None
    off_val = int(row["pod_offset_days"]) if pd.notna(row["pod_offset_days"]) else None
    if tt_val is None or off_val is None:
        return None
    return {
        "article_id": product_row.get("Article_ID"),
        "product_description": product_row.get("Product_Description"),
        "supplier_name": product_row.get("Supplier_Name"),
        "material": product_row.get("Material"),
        "pol_country": pol,
        "pod_country": pod_s,
        "tt_days": tt_val,
        "pod_offset_days": off_val,
        "recommended_lead_days": tt_val + off_val,
    }
