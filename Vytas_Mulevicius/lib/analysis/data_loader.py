import os
import tempfile
import urllib.request
import streamlit as st
import polars as pl

_TREE_NAMES = ('Events', 'DecayTree', 'mini', 'tree')
_DOWNLOAD_CHUNK = 1024 * 1024  # 1 MB per read
_WARN_SIZE_BYTES = 500 * 1024 * 1024  # warn above 500 MB


def _find_tree(f):
    all_trees = [k for k, v in f.items(recursive=True) if hasattr(v, "arrays")]
    if not all_trees:
        st.error("No TTree found in file.")
        st.stop()
    return next((k for k in all_trees if any(p in k for p in _TREE_NAMES)), all_trees[0])


def _format_mb(n_bytes: int) -> str:
    return f"{n_bytes / 1_048_576:.1f} MB"


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pl.DataFrame:
    """
    Loads a CSV or ROOT file into a Polars DataFrame.

    Accepts local paths (.csv, .root), HTTP URLs, and XRootD paths starting with
    'root://'. ROOT files are opened via uproot; the first tree whose name contains
    'Events', 'DecayTree', 'mini', or 'tree' is selected, then converted to Polars
    via Arrow. Calls st.stop() on unrecognized formats.
    """
    is_csv = path.lower().split('?')[0].endswith('.csv')
    if is_csv:
        return pl.read_csv(path)

    # Heuristic: check for standard extension or CERN indexed storage pattern
    is_cern_files_proxy = 'opendata.cern.ch/record/' in path and '/files/' in path
    if path.lower().split('?')[0].endswith('.root') or path.startswith('root://') or (is_cern_files_proxy and not is_csv):
        if path.startswith('root://'):
            st.error(
                "⚠️ **XRootD streaming is not available** — the `fsspec-xrootd` package is not "
                "installed in this environment.\n\n"
                "**What to do:** Go to the **CERN Explorer** page, find this file, and click "
                "**🌊 Stream** to load it over HTTP instead."
            )
            st.stop()
            return pl.DataFrame()

        import uproot
        import awkward as ak
        with uproot.open(path) as f:
            tree_name = _find_tree(f)
            st.info(f"📍 Loading tree: `{tree_name}`")
            ak_array = f[tree_name].arrays()
            return pl.from_arrow(ak.to_arrow_table(ak_array, extensionarray=False))

    st.error(f"Unsupported file format: {path}")
    st.stop()


def stream_root_data(path: str) -> pl.DataFrame:
    """
    Streams a remote ROOT file, showing two-phase live progress:
      1. Download phase — progress bar + MB counter as bytes arrive.
      2. Iterate phase — 10k-event chunks with a rolling data preview.

    Many CERN ROOT files have inconsistent fEND/fNbytesKeys headers that prevent
    uproot from reading the directory structure over HTTP. Downloading to a temp
    file first avoids this; uproot then reads a local file whose size is correct.
    Results are NOT cached — callers should store in st.session_state.
    """
    import uproot
    import awkward as ak

    tmp_path = None
    try:
        tmp_path = _download_with_progress(path)
        return _iterate_with_preview(tmp_path)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _download_with_progress(url: str) -> str:
    req_head = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_head) as head:
        total = int(head.headers.get('Content-Length', 0))

    if total and total > _WARN_SIZE_BYTES:
        st.warning(
            f"⚠️ Large file: **{_format_mb(total)}** — download may take several minutes. "
            "Consider using a smaller sample if available."
        )
    st.info(f"📥 Downloading {'(' + _format_mb(total) + ')' if total else ''}...")
    col_prog, col_stat = st.columns([3, 1])
    with col_prog:
        dl_bar = st.progress(0.0)
    with col_stat:
        dl_status = st.empty()

    tmp = tempfile.NamedTemporaryFile(suffix='.root', delete=False)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            downloaded = 0
            while True:
                chunk = resp.read(_DOWNLOAD_CHUNK)
                if not chunk:
                    break
                tmp.write(chunk)
                downloaded += len(chunk)
                dl_bar.progress(min(downloaded / total, 1.0) if total else 0.0)
                dl_status.metric("Downloaded", _format_mb(downloaded))
    except Exception as exc:
        tmp.close()
        os.unlink(tmp.name)
        raise exc

    tmp.close()
    if total and downloaded < total:
        os.unlink(tmp.name)
        raise OSError(
            f"Download incomplete: received {_format_mb(downloaded)} of {_format_mb(total)}. "
            "The connection may have been reset. Try again or use a smaller file."
        )
    dl_bar.empty()
    dl_status.empty()
    return tmp.name


def _iterate_with_preview(local_path: str) -> pl.DataFrame:
    import uproot
    import awkward as ak

    with uproot.open(local_path) as f:
        tree_name = _find_tree(f)
        tree = f[tree_name]
        total = tree.num_entries

        st.info(f"📍 Processing tree: `{tree_name}` — {total:,} total events")
        col_prog, col_stat = st.columns([3, 1])
        with col_prog:
            iter_bar = st.progress(0.0)
        with col_stat:
            iter_status = st.empty()
        preview = st.empty()

        # Filter out branches that cannot be read as awkward arrays at iterate time.
        # Two classes of problematic branches exist in real CERN files:
        #  1. Empty/bookkeeping branches (num_entries != total) — cause length-mismatch ValueError
        #  2. Object branches (TObjArray etc.) that awkward cannot represent — CannotBeAwkward
        # Using filter_branch ensures the check runs for friend-tree branches too.
        def _branch_ok(branch):
            try:
                if branch.num_entries != total:
                    return False
                # 1. Check if awkward can even form the type
                branch.interpretation.awkward_form(branch.file)
                # 2. Test read the first entry to catch DeserializationErrors (common in RAW/RECO frameworks)
                branch.array(entry_start=0, entry_stop=1, library="ak")
                return True
            except (Exception, uproot.deserialization.DeserializationError):
                # Omit branches that cannot be deserialized safely in a Python environment
                return False

        chunks = []
        loaded = 0
        for chunk in tree.iterate(filter_branch=_branch_ok, step_size=10_000, library="ak"):
            chunk_df = pl.from_arrow(ak.to_arrow_table(chunk, extensionarray=False))
            chunks.append(chunk_df)
            loaded += len(chunk_df)
            iter_bar.progress(min(loaded / total, 1.0))
            iter_status.metric("Events", f"{loaded:,}")
            preview.dataframe(chunk_df.head(5).to_pandas(), use_container_width=True)

        iter_bar.empty()
        iter_status.empty()
        preview.empty()

    if not chunks:
        st.error(
            "⚠️ No data could be read from this ROOT tree — all branches use "
            "unsupported complex object types (e.g. TObjArray). "
            "Try a different file or tree."
        )
        st.stop()
        return pl.DataFrame()

    return pl.concat(chunks)
