from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[3]
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import macro_indicator_pipeline as mip
import macro_indicator_helpers as mih


class FakeResponse:
    def __init__(self, payload: Any):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> Any:
        return self._payload


def test_build_series_registry_core_scope_and_counts() -> None:
    registry = mip.build_series_registry(country_code="LT")

    assert len(registry) >= 16
    assert set(registry["source_id"].unique()) == {"world_bank", "eurostat", "imf"}

    by_indicator = registry.groupby("indicator_id")["source_id"].nunique().to_dict()
    assert by_indicator["gdp_current_usd"] >= 3
    assert by_indicator["inflation_cpi_yoy"] >= 3
    assert by_indicator["lending_interest_rate"] >= 2


def test_build_series_registry_has_exact_and_proxy_mapping_quality() -> None:
    registry = mip.build_series_registry(country_code="LT")
    qualities = set(registry["mapping_quality"].unique())

    assert "exact" in qualities
    assert "proxy" in qualities


def test_resolved_url_patterns_are_constructed_for_core_sources() -> None:
    registry = mip.build_series_registry(country_code="LT")

    wb = registry[(registry["source_id"] == "world_bank") & (registry["indicator_id"] == "gdp_current_usd")].iloc[0]
    es = registry[(registry["source_id"] == "eurostat") & (registry["indicator_id"] == "gdp_current_usd")].iloc[0]
    imf = registry[(registry["source_id"] == "imf") & (registry["indicator_id"] == "gdp_current_usd")].iloc[0]

    assert "api.worldbank.org" in wb["resolved_url"]
    assert "NY.GDP.MKTP.CD" in wb["resolved_url"]

    assert "ec.europa.eu/eurostat" in es["resolved_url"]
    assert "nama_10_gdp" in es["resolved_url"]
    assert "geo=LT" in es["resolved_url"]

    assert "external/datamapper" in imf["resolved_url"]
    assert imf["resolved_url"].endswith("/NGDPD/LTU")


def test_fetch_world_bank_json_handles_pagination(monkeypatch) -> None:
    def fake_resolve(url: str, timeout: int = 20) -> str:
        return url

    def fake_get(url: str, timeout: int = 20):
        if "page=2" in url:
            return FakeResponse([
                {"pages": 2},
                [{"date": "2019", "value": 2}],
            ])
        if "page=1" in url:
            return FakeResponse([
                {"pages": 2},
                [{"date": "2020", "value": 1}],
            ])
        return FakeResponse([{"pages": 0}, []])

    monkeypatch.setattr(mih, "resolve_url", fake_resolve)
    monkeypatch.setattr(mih.requests, "get", fake_get)

    rows = mip.fetch_world_bank_json("https://api.worldbank.org/v2/country/LT/indicator/NY.GDP.MKTP.CD")
    assert len(rows) == 2
    assert {row["date"] for row in rows} == {"2019", "2020"}


def test_resolve_series_endpoints_sets_reason_codes(monkeypatch) -> None:
    registry = mip.build_series_registry(country_code="LT").head(2).copy()
    registry.loc[registry.index[0], "resolved_url"] = None
    registry.loc[registry.index[0], "indicator_code"] = None

    def fake_validate(url: str, timeout: int = 20) -> Dict[str, Any]:
        return {
            "resolved_url": url,
            "status": 200,
            "content_type": "application/json",
            "content": b"{}",
        }

    monkeypatch.setattr(mih, "validate_endpoint", fake_validate)

    resolved = mip.resolve_series_endpoints(registry)

    first = resolved.iloc[0]
    second = resolved.iloc[1]

    assert first["endpoint_status"] == "unresolved"
    assert first["resolution_reason"] == "missing_required_parameters"
    assert second["endpoint_status"] == "resolved"
    assert second["resolution_reason"] == "ok"


def test_flatten_eurostat_jsonstat_payload() -> None:
    payload = {
        "id": ["freq", "time"],
        "size": [1, 3],
        "dimension": {
            "freq": {"category": {"index": {"A": 0}}},
            "time": {"category": {"index": {"2020": 0, "2021": 1, "2022": 2}}},
        },
        "value": {"0": 1.0, "1": 2.0, "2": 3.0},
    }

    df = mip.flatten_eurostat_jsonstat(payload)

    assert len(df) == 3
    assert set(df.columns) >= {"freq", "time", "value"}
    assert set(df["time"].tolist()) == {"2020", "2021", "2022"}


def test_normalize_imf_datamapper_payload() -> None:
    payload = {
        "values": {
            "NGDPD": {
                "LTU": {
                    "2019": 54.0,
                    "2020": 56.5,
                }
            }
        }
    }

    df = mip.normalize_imf_datamapper_payload(payload, indicator_code="NGDPD", country_iso3="LTU")

    assert len(df) == 2
    assert set(df.columns) == {"period", "year", "value"}
    assert df["year"].tolist() == [2019, 2020]


def test_fetch_and_normalize_series_aggregates_monthly_to_annual(monkeypatch) -> None:
    payload = {
        "id": ["freq", "unit", "coicop", "geo", "time"],
        "size": [1, 1, 1, 1, 3],
        "dimension": {
            "freq": {"category": {"index": {"M": 0}}},
            "unit": {"category": {"index": {"RCH_A": 0}}},
            "coicop": {"category": {"index": {"CP00": 0}}},
            "geo": {"category": {"index": {"LT": 0}}},
            "time": {"category": {"index": {"2020-01": 0, "2020-02": 1, "2021-01": 2}}},
        },
        "value": {"0": 1.0, "1": 3.0, "2": 5.0},
    }

    resolved_registry = pd.DataFrame(
        [
            {
                "indicator_id": "inflation_cpi_yoy",
                "source_id": "eurostat",
                "source_name": "Eurostat",
                "dataset_code": "prc_hicp_manr",
                "indicator_code": None,
                "series_key": "geo=LT&freq=M&coicop=CP00&unit=RCH_A",
                "mapping_quality": "proxy",
                "specificity_note": "Monthly series",
                "frequency_raw": "M",
                "unit_raw": "RCH_A",
                "country_code": "LT",
                "country_code_iso3": "LTU",
                "resolved_url": "https://example.test/eurostat",
                "endpoint_status": "resolved",
            }
        ]
    )

    def fake_validate(url: str, timeout: int = 20) -> Dict[str, Any]:
        return {
            "resolved_url": url,
            "status": 200,
            "content_type": "application/json",
            "content": json.dumps(payload).encode("utf-8"),
        }

    monkeypatch.setattr(mih, "validate_endpoint", fake_validate)

    normalized = mip.fetch_and_normalize_series(resolved_registry)

    assert len(normalized) == 2
    assert normalized["year"].tolist() == [2020, 2021]
    assert normalized["value"].round(4).tolist() == [2.0, 5.0]
    assert set(normalized["frequency_raw"].unique()) == {"M"}
    assert set(normalized["frequency_canonical"].unique()) == {"A"}
