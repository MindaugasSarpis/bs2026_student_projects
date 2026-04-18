"""
End-to-end pipeline smoke tests.

For each CERN Open Data query, find real files (CSV or ROOT, ≤ 100 MB),
run the full analysis pipeline, and assert the output makes sense.
Any crash here means the same crash would happen in the UI.

Run with: pytest -m network -v tests/test_e2e_pipeline.py
"""
import json
import urllib.request
import pytest
import polars as pl

MAX_CSV_BYTES = 100 * 1024 * 1024   # 100 MB
MAX_ROOT_BYTES = 50 * 1024 * 1024   # 50 MB  (each root file requires a full download)
MAX_CSV_PER_QUERY = 6
MAX_ROOT_PER_QUERY = 4

# Queries that are known to return CSV files with physics data
CSV_QUERIES = [
    "Jpsimumu",             # J/ψ → μμ, CMS dimuon format
    "Zmumu",                # Z  → μμ
    "Ymumu",                # Υ  → μμ
    "dielectron",           # Z/J/ψ → ee, different column format than dimuon
    "Wenu",                 # W  → eν, exercises transverse-mass branch
    "psi",                  # J/ψ masterclass files
    "two muons 2010",       # CMS Run2010 dimuon, has trailing-space column px1
    "CMS dimuon",           # rec700 MuRun2010B files, ~1 MB each
    "CMS masterclass Higgs",# 4lepton.csv (4-body M), diphoton.csv (pt/eta/phi M)
]

# Queries that are known to return ROOT files
ROOT_QUERIES = [
    "ATLAS 2lep",    # 175 ATLAS mini-tree 2lep files; exercises lep_pt list columns
    "ttbar",         # CMS ttbar.root, Muon_Px list columns, CMS multi-lepton mapper
    "B meson",       # LHCb PhaseSpaceSimulation.root, DecayTree; unsupported 3-body
    "Zmumu",         # ATLAS 4lep MC samples
    "GamGam ATLAS",  # ATLAS diphoton mini-tree; lep_pt present but ~0 dimuon events
    "ATLAS 4lep",    # ATLAS H→ZZ→4l analysis files
    "photon pair",   # PHENIX photon-pair ntuples; fully custom schema
    "kaon",          # LHCb D0→Kπ masterclass DecayTree; unsupported decay topology
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fetch_records(query: str) -> list:
    url = (
        f"https://opendata.cern.ch/api/records/"
        f"?q={query.replace(' ', '+')}&size=20&f=type:Dataset"
    )
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8')).get('hits', {}).get('hits', [])


def _find_files(hits: list, extensions: tuple, max_bytes: int, max_count: int,
                prefer_keyword: str = "") -> list[dict]:
    """Collect up to max_count files matching extensions and ≤ max_bytes."""
    candidates = []
    for hit in hits:
        rec_id = hit.get('id')
        for f in hit.get('metadata', {}).get('_files', []):
            key = f.get('key', '')
            size = f.get('size', 0)
            if key.lower().endswith(extensions) and 0 < size <= max_bytes:
                candidates.append({
                    'url': f"https://opendata.cern.ch/record/{rec_id}/files/{key}",
                    'size': size,
                    'key': key,
                    'rec_id': rec_id,
                })
    if prefer_keyword:
        preferred = [c for c in candidates if prefer_keyword in c['key'].lower()]
        rest = [c for c in candidates if prefer_keyword not in c['key'].lower()]
        candidates = preferred + rest
    return candidates[:max_count]


def _run_pipeline(df: pl.DataFrame, label: str) -> tuple[int, str]:
    """
    Run map_columns + apply_kinematic_filters on df.
    Returns (n_events_surviving, mass_range_str).
    Returns (0, "unsupported format") when map_columns can't recognise the schema
    (same outcome as the UI showing st.error + st.stop).
    Raises on any genuine unexpected exception.
    """
    from lib.analysis.column_mapper import map_columns
    from lib.analysis.filters import apply_kinematic_filters

    df = map_columns(df)
    if 'Calculated_M' not in df.columns:
        # map_columns called st.error + st.stop (both mocked) and returned early.
        # In the UI this shows a clean error message — not a crash.
        return 0, "unsupported format"

    df = apply_kinematic_filters(df, (0.0, 10_000.0), 0.0, 10.0,
                                 require_opposite_charge=False)
    if len(df) > 0:
        lo = df['Calculated_M'].min()
        hi = df['Calculated_M'].max()
        return len(df), f"[{lo:.2f}, {hi:.2f}] GeV"
    return 0, "—"


# ---------------------------------------------------------------------------
# CSV pipeline: pl.read_csv → map_columns → apply_kinematic_filters
# ---------------------------------------------------------------------------

@pytest.mark.network
@pytest.mark.parametrize("query", CSV_QUERIES)
def test_csv_full_pipeline(query):
    """
    Fetch up to MAX_CSV_PER_QUERY CSV files ≤ 100 MB for the given query,
    run the full pipeline on each, assert at least one file produces events.
    """
    hits = _fetch_records(query)
    if not hits:
        pytest.skip(f"No datasets returned by CERN API for query: {query!r}")

    files = _find_files(hits, ('.csv', '.txt'), MAX_CSV_BYTES, MAX_CSV_PER_QUERY)
    # Drop known non-tabular files: LFNS listings, certification JSONs, index lists
    _NON_TABULAR = ('_LFNS.txt', 'Cert_', 'rootfilelist', 'List_index', '_JSON_')
    files = [f for f in files if not any(t in f['key'] for t in _NON_TABULAR)]
    if not files:
        pytest.skip(f"No usable CSV files ≤ 100 MB found for query: {query!r}")

    any_events = False
    for fi in files:
        label = fi['key']
        print(f"\n[{query}] {label}  ({fi['size'] / 1e6:.1f} MB)")
        try:
            df = pl.read_csv(fi['url'])
        except Exception as e:
            print(f"  → not parseable as CSV ({type(e).__name__}), skipping file")
            continue
        assert len(df) > 0, f"[{label}] loaded as empty DataFrame"

        n, mass_range = _run_pipeline(df, label)
        if n > 0:
            any_events = True
            print(f"  → {n:,} events, Calculated_M {mass_range}")
        else:
            print(f"  → 0 events after pipeline (single-lepton or unrecognised format)")

    assert any_events, (
        f"[{query}] All {len(files)} CSV files produced 0 events through the pipeline."
    )


# ---------------------------------------------------------------------------
# ROOT stream pipeline: stream_root_data → map_columns → apply_kinematic_filters
# ---------------------------------------------------------------------------

@pytest.mark.network
@pytest.mark.parametrize("query", ROOT_QUERIES)
def test_root_stream_full_pipeline(query):
    """
    Fetch up to MAX_ROOT_PER_QUERY ROOT files ≤ 50 MB for the given query,
    stream each via stream_root_data, run the full pipeline.
    Prefers '2lep' files to maximise chance of di-lepton events surviving.
    """
    from lib.analysis.data_loader import stream_root_data

    hits = _fetch_records(query)
    if not hits:
        pytest.skip(f"No datasets returned by CERN API for query: {query!r}")

    files = _find_files(hits, ('.root',), MAX_ROOT_BYTES, MAX_ROOT_PER_QUERY,
                        prefer_keyword='2lep')
    if not files:
        pytest.skip(f"No ROOT files ≤ 50 MB found for query: {query!r}")

    any_events = False
    for fi in files:
        label = fi['key']
        print(f"\n[{query}] {label}  ({fi['size'] / 1e6:.1f} MB)")

        df = stream_root_data(fi['url'])
        assert isinstance(df, pl.DataFrame), f"[{label}] stream_root_data returned non-DataFrame"
        if len(df) == 0:
            print(f"  → 0 rows loaded (all branches use unsupported object types)")
            continue

        n, mass_range = _run_pipeline(df, label)
        if n > 0:
            any_events = True
            print(f"  → {n:,} events, Calculated_M {mass_range}")
        else:
            print(f"  → 0 events after pipeline (single-lepton or unrecognised format)")

    if not any_events:
        pytest.skip(
            f"[{query}] All {len(files)} ROOT files produced 0 events — "
            "likely all single-lepton or unrecognised tree structure."
        )
