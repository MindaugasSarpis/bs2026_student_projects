import streamlit as st
import math
from lib.ui_utils import apply_branding, render_sidebar_footer
from lib.exploration.cern_api import get_cern_data, QUICK_PICKS
from lib.exploration.file_renderer import render_csv_files, render_root_files

st.set_page_config(page_title="CERN Explorer | Portal", page_icon="⚛️", layout="wide")
apply_branding()

st.markdown("""
    <style>
    .metric-card { background: rgba(255,255,255,0.03); padding: 15px; border-radius: 8px; text-align: center; }
    </style>
""", unsafe_allow_html=True)

# --- Session state defaults ---
if 'search_query' not in st.session_state:
    st.session_state.search_query = "Jpsimumu"
if 'active_preview_id' not in st.session_state:
    st.session_state.active_preview_id = None
if 'nav_to_analysis' not in st.session_state:
    st.session_state.nav_to_analysis = False
if 'expanded_rec_id' not in st.session_state:
    st.session_state.expanded_rec_id = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 1

if st.session_state.nav_to_analysis:
    st.session_state.nav_to_analysis = False
    st.switch_page("pages/1_Analysis.py")

# --- Search UI ---
st.title("🔍 Explore CERN Open Data")
st.write("Search the live CERN Open Data portal for authentic particle physics datasets.")

col_search, col_filter = st.columns([3, 1])
with col_search:
    st.text_input("Enter search terms (e.g., 'Jpsimumu', 'DoubleMu', 'Run 2011')", key="search_query")
with col_filter:
    st.write("")
    only_csv = st.checkbox("Only CSV-compatible", value=True)

# --- Sidebar Controls ---
st.sidebar.header("Search Settings")
max_results = st.sidebar.slider("Max Results", 10, 100, 20, step=10)

st.write("🎯 **Quick Picks (Guaranteed CSVs):**")
qp_cols = st.columns(4)
for i, (label, query) in enumerate(QUICK_PICKS.items()):
    with qp_cols[i]:
        st.button(label, key=f"qp_{i}",
                  on_click=lambda q=query: st.session_state.update(search_query=q))

# --- Results ---
if st.session_state.search_query:
    if st.session_state.get('_last_query') != (st.session_state.search_query, only_csv, max_results):
        st.session_state.expanded_rec_id = None
        st.session_state.current_page = 1
        st.session_state._last_query = (st.session_state.search_query, only_csv, max_results)

    with st.spinner(f"Querying CERN Open Data API (Page {st.session_state.current_page})..."):
        result_data = get_cern_data(st.session_state.search_query, only_csv, size=max_results, page=st.session_state.current_page)

    if "error" in result_data:
        st.error(f"Error querying CERN API: {result_data['error']}")
    else:
        hits = result_data.get('hits', {}).get('hits', [])
        if not hits:
            st.warning("No datasets found for this search.")
        else:
            st.subheader(f"Found {len(hits)} matching records")
            for hit in hits:
                metadata = hit.get('metadata', {})
                title = metadata.get('title', 'Unknown Title')
                rec_id = hit.get('id')
                is_preview_active = st.session_state.active_preview_id == rec_id
                show_files = is_preview_active or (st.session_state.expanded_rec_id == rec_id)

                with st.expander(f"📚 {title} (ID: {rec_id})", expanded=show_files):
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("Experiment", ", ".join(metadata.get('experiment', ['N/A'])))
                    with m2:
                        st.metric("Type", metadata.get('type', {}).get('secondary', ['Dataset'])[0])
                    with m3:
                        st.metric("Year", metadata.get('date_published', 'N/A'))
                    with m4:
                        st.metric("Run", ", ".join(metadata.get('run_period', ['N/A'])))

                    st.markdown("---")
                    st.write(metadata.get('description', 'Detailed information available on the CERN Open Data portal.'))

                    if 'methodology' in metadata:
                        with st.expander("🔬 Methodology & Selection Criteria"):
                            st.write(metadata['methodology'].get('description', ''), unsafe_allow_html=True)

                    st.markdown(f"**Official Record:** [opendata.cern.ch/record/{rec_id}](https://opendata.cern.ch/record/{rec_id})")

                    files = metadata.get('_files', [])
                    if not files:
                        indices = metadata.get('_file_indices', [])
                        if indices and isinstance(indices, list):
                            files = indices[0].get('files', [])
                    compatible = []
                    root_files = []
                    for f in files:
                        # Smart identification: check key, filename, and uri
                        name = f.get('filename') or f.get('key', '')
                        path = f.get('uri') or f.get('key', '').split('?')[0]
                        
                        target = name.lower() if name else path.lower()
                        
                        if target.endswith(('.csv', '.txt', '.json')):
                            compatible.append(f)
                        elif target.endswith('.root'):
                            root_files.append(f)

                    if show_files:
                        if compatible:
                            render_csv_files(compatible, rec_id, is_preview_active)
                        if root_files:
                            render_root_files(root_files, rec_id)
                        if not compatible and not root_files:
                            formats = metadata.get('distribution', {}).get('formats', [])
                            fmt = ", ".join(formats).upper() if formats else "ROOT/DST"
                            st.warning(f"⚠️ This dataset uses **{fmt}** format, which is not supported for direct browser preview.")
                    else:
                        parts = []
                        if compatible:
                            parts.append(f"{len(compatible)} CSV")
                        if root_files:
                            parts.append(f"{len(root_files)} ROOT")
                        label = f"📂 Show files ({', '.join(parts)})" if parts else "⚠️ No data files"
                        if parts:
                            st.button(
                                label,
                                key=f"show_{rec_id}",
                                on_click=lambda r=rec_id: st.session_state.update(expanded_rec_id=r),
                            )
                        else:
                            st.caption(label)

            # --- Pagination Controls ---
            st.markdown("---")
            nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
            
            total_hits = result_data.get('hits', {}).get('total', 0)
            max_pages = math.ceil(total_hits / max_results) if total_hits > 0 else 1
            
            with nav_col1:
                if st.button("⬅️ Previous Page", disabled=st.session_state.current_page <= 1):
                    st.session_state.current_page -= 1
                    st.rerun()
            
            with nav_col2:
                st.markdown(f"<p style='text-align: center;'>Page <b>{st.session_state.current_page}</b> of {max_pages}<br><small>{total_hits:,} total records</small></p>", unsafe_allow_html=True)
                
            with nav_col3:
                if st.button("Next Page ➡️", disabled=st.session_state.current_page >= max_pages):
                    st.session_state.current_page += 1
                    st.rerun()

st.info("💡 **Navigation:** Use the sidebar on the left to head back to the 'Analysis' module with your own local data.")

render_sidebar_footer()
