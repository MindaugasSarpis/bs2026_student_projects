import os
import urllib.request
import pandas as pd
import streamlit as st
from lib.download_data import download_single_file
from lib.exploration.cern_api import CernFileInfo, format_size


def render_csv_files(compatible: list[CernFileInfo], rec_id: str | int, is_active: bool) -> None:
    """
    Renders a list of CSV files from a CERN Open Data record.

    Each file row shows Preview / Stream / Fetch buttons. is_active controls whether
    the inline data preview panel expands beneath the currently selected file.
    """
    st.info(f"📊 Found {len(compatible)} compatible data files:")
    for f in compatible:
        fname = f.get('key')
        fsize = format_size(f.get('size'))
        furl = f"https://opendata.cern.ch/record/{rec_id}/files/{fname}"

        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        with c1:
            st.markdown(f"- **{fname}** (`{fsize}`)")
        with c2:
            st.button("👁️ Preview", key=f"pbtn_{rec_id}_{fname}",
                      on_click=_handle_preview, args=(rec_id, fname, furl))
        with c3:
            st.button("🌊 Stream", key=f"strbtn_{rec_id}_{fname}",
                      on_click=_stream_to_analysis, args=(furl,))
        with c4:
            _render_fetch_button(fname, furl, key=f"dlbtn_{rec_id}_{fname}")

        if is_active and st.session_state.get('active_preview_fname') == fname:
            _render_preview_content()


def render_root_files(root_files: list[CernFileInfo], rec_id: str | int) -> None:
    """Renders ROOT/DST files from a CERN record with Peek / Stream / Fetch / XRootD buttons."""
    st.divider()
    st.markdown("⚛️ **ROOT/DST Files Detected**")
    st.caption("These files contain complex physics objects. You can 'Peek' to see their internal structure.")
    for f in root_files:
        fname = f.get('key')
        fsize = format_size(f.get('size'))
        furl = f"https://opendata.cern.ch/record/{rec_id}/files/{fname}"

        rc1, rc2, rc3, rc4, rc5 = st.columns([3, 1, 1, 1, 1])
        with rc1:
            st.markdown(f"- `{fname}` (`{fsize}`)")
        with rc2:
            if st.button("🔍 Peek", key=f"peek_{rec_id}_{fname}"):
                _peek_root_file(furl, fname, rec_id)
        with rc3:
            st.button("🌊 Stream", key=f"strr_{rec_id}_{fname}",
                      on_click=_stream_to_analysis, args=(furl,))
        with rc4:
            _render_fetch_button(fname, furl, key=f"dlr_{rec_id}_{fname}")
        with rc5:
            st.button("🔗 XRootD", key=f"xrdb_{rec_id}_{fname}",
                      help="Copy XRootD path for high-speed streaming",
                      on_click=lambda u=furl: st.toast(
                          f"XRootD Suggestion: root://eospublic.cern.ch//eos/opendata/{u.split('files/')[-1]}",
                          icon="⚛️"
                      ))

        if st.session_state.get('root_active_id') == rec_id and st.session_state.get('root_active_fname') == fname:
            _render_root_tree_inspector(furl, rec_id, fname)


# --- Internal helpers ---

def _handle_preview(rec_id: str | int, fname: str, furl: str) -> None:
    st.session_state.active_preview_id = rec_id
    st.session_state.active_preview_fname = fname
    try:
        if fname.endswith('.csv'):
            st.session_state.preview_content = pd.read_csv(furl, nrows=20)
            st.session_state.preview_type = 'df'
        else:
            req_f = urllib.request.Request(furl, headers={'User-Agent': 'Mozilla/5.0'})
            st.session_state.preview_content = urllib.request.urlopen(req_f).read(1000).decode('utf-8')
            st.session_state.preview_type = 'text'
    except Exception as e:
        st.session_state.preview_error = str(e)


def _stream_to_analysis(url: str) -> None:
    st.session_state.stream_url = url
    st.session_state.data_source = "Remote Stream (XRootD/HTTP)"
    st.session_state.nav_to_analysis = True


def _render_fetch_button(fname: str, furl: str, key: str) -> None:
    if os.path.exists(os.path.join('data', fname)):
        st.button("✅ Stored", key=key, disabled=True)
    else:
        if st.button("📥 Fetch", key=key):
            with st.spinner(f"Fetching {fname}..."):
                download_single_file(furl, fname)
            st.success("Downloaded! Refreshing...")
            st.rerun()


def _render_preview_content() -> None:
    st.markdown("### 👁️ Data Preview")
    if 'preview_error' in st.session_state:
        st.error(st.session_state.preview_error)
        del st.session_state.preview_error
    elif st.session_state.get('preview_type') == 'df':
        st.dataframe(st.session_state.preview_content, width='stretch')
    else:
        st.code(st.session_state.preview_content, language='text')


def _peek_root_file(furl: str, fname: str, rec_id: str | int) -> None:
    try:
        import uproot
        with st.spinner("Analyzing remote ROOT header..."):
            with uproot.open(furl) as root_file:
                st.session_state.root_active_id = rec_id
                st.session_state.root_active_fname = fname
                st.session_state.root_keys = root_file.keys()
                st.success(f"Successfully bridged to `{fname}`")
    except Exception as e:
        st.error(f"Network error peeking ROOT file: {e}")
        if "outside expected range" in str(e).lower():
            st.warning("⚠️ **Header Fragmentation Detected:** This file's internal directory is fragmented across the network.")
            st.info(
                "💡 **Solution:** Click **🌊 Stream** instead. Streaming uses a robust two-phase download that "
                "handles fragmented headers perfectly by buffering the file locally."
            )
        else:
            st.info("💡 **Tip:** This large or complex file might require a local download (**📥 Fetch**) for full inspection.")


def _render_root_tree_inspector(furl: str, rec_id: str | int, fname: str) -> None:
    with st.container():
        st.markdown("---")
        st.write("**Found Trees/Directories:**")
        all_keys = st.session_state.root_keys
        st.write(all_keys)
        selected_tree = st.selectbox(
            "Select a Tree to inspect branches",
            ["(Select)"] + all_keys,
            key=f"tsel_{rec_id}_{fname}",
        )
        if selected_tree != "(Select)":
            try:
                import uproot
                with st.spinner(f"Reading branches from `{selected_tree}`..."):
                    with uproot.open(furl) as root_file:
                        st.write(f"**Branches in `{selected_tree}`:**")
                        st.json(root_file[selected_tree].keys())
            except Exception as e:
                st.error(f"Could not read branches: {e}")
                if "outside expected range" in str(e).lower():
                    st.info("💡 **Tip:** This tree's metadata is too complex for a network peek. Use **🌊 Stream** to analyze it instead.")
