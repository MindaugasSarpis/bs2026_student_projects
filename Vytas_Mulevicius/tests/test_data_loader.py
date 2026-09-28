import pytest
import polars as pl
import tempfile, os, urllib.request

# Small ATLAS Open Data file — known to have inconsistent fEND/fNbytesKeys headers
CERN_HTTP_ROOT = "https://opendata.cern.ch/record/15003/files/data_A.2lep.root"


@pytest.mark.network
def test_stream_root_data_returns_nonempty_dataframe():
    """
    Integration: downloads data_A.2lep.root to a temp file, opens it with uproot,
    and iterates in chunks. Verifies the result is a non-empty Polars DataFrame.
    Run with: pytest -m network
    """
    from lib.analysis.data_loader import stream_root_data

    df = stream_root_data(CERN_HTTP_ROOT)

    assert isinstance(df, pl.DataFrame), "result must be a Polars DataFrame"
    assert len(df) > 0, "DataFrame must not be empty"
    assert len(df.columns) > 0, "DataFrame must have at least one column"


@pytest.mark.network
def test_stream_root_data_all_chunks_present():
    """
    Downloads the file, opens it directly with uproot to get num_entries, then
    streams via stream_root_data and checks that every event was loaded.
    """
    import uproot
    from lib.analysis.data_loader import stream_root_data

    tmp = tempfile.NamedTemporaryFile(suffix='.root', delete=False)
    try:
        req = urllib.request.Request(CERN_HTTP_ROOT, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            tmp.write(resp.read())
        tmp.close()

        with uproot.open(tmp.name) as f:
            trees = [k for k, v in f.items(recursive=True) if hasattr(v, "arrays")]
            expected_rows = f[trees[0]].num_entries
    finally:
        tmp.close()
        if os.path.exists(tmp.name):
            os.unlink(tmp.name)

    df = stream_root_data(CERN_HTTP_ROOT)

    assert len(df) == expected_rows, (
        f"expected {expected_rows} events from uproot, got {len(df)}"
    )
