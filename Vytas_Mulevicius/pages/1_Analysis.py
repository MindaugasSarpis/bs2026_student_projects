import streamlit as st
import os
from lib.download_data import get_datasets, download_dataset
from lib.ui_utils import apply_branding, render_sidebar_footer
from lib.exploration.inspect_root import get_root_structure, get_branch_details
from lib.analysis.dataset_metadata import get_metadata, build_file_options
from lib.analysis.data_loader import load_data, stream_root_data
from lib.analysis.column_mapper import map_columns
from lib.analysis.filters import apply_kinematic_filters
from lib.analysis.plots.mass_histogram import render_mass_histogram
from lib.analysis.plots.event_display_3d import render_3d_event_display
from lib.analysis.plots.event_animation_3d import render_3d_animation
from lib.analysis.identification import find_primary_peak, match_particle

st.set_page_config(page_title="CERN Explorer | Analysis", page_icon="⚛️", layout="wide")
apply_branding()

# --- Sidebar: Dataset Selection ---
st.sidebar.header("Dataset Selection")
if not os.path.exists('data'):
    os.makedirs('data', exist_ok=True)

available_files = sorted([f for f in os.listdir('data') if f.endswith(('.csv', '.root'))])
data_source = st.sidebar.radio("Data Source", ["Local Storage", "Remote Stream (XRootD/HTTP)"], key="data_source")

if data_source == "Local Storage":
    if not available_files:
        st.warning("📂 No datasets found. Go to the **Explorer** page to download data!")
        st.stop()
    display_options, file_map = build_file_options(available_files)
    dataset_choice = st.sidebar.selectbox("Choose a local dataset", display_options)
    selected_file = file_map[dataset_choice]
else:
    initial_url = st.session_state.get('stream_url', "")
    selected_file = st.sidebar.text_input("Enter ROOT/CSV URL", value=initial_url, placeholder="root://eospublic.cern.ch//eos/...")
    if not selected_file:
        st.info("💡 **Tip:** Go to the **Explorer** page and click 'Stream' on a dataset, or paste a URL here.")
        st.stop()

# --- Metadata ---
is_csv = selected_file.lower().split('?')[0].endswith('.csv')
is_cern_files_proxy = 'opendata.cern.ch/record/' in selected_file and '/files/' in selected_file
is_root = (selected_file.lower().split('?')[0].endswith('.root') or selected_file.startswith('root://') or is_cern_files_proxy) and not is_csv
meta = get_metadata(selected_file)

st.title(f"{meta.particle_name} Physical Analysis")
if data_source == "Remote Stream (XRootD/HTTP)":
    st.caption(f"🌐 Streaming from: `{selected_file}`")
st.markdown(
    "Exploring authentic CERN Open Data. For CSVs, we use Polars for speed. "
    "For **ROOT/DST** files, we use **Uproot** to extract columnar data directly into the analysis pipeline."
)

# --- Local file check + download ---
if data_source == "Local Storage":
    data_path = f'data/{selected_file}'
    if not os.path.exists(data_path):
        st.warning(f"⚠️ Dataset **{selected_file}** not found locally.")
        if st.button("Download Required Datasets", type="primary"):
            datasets = get_datasets()
            os.makedirs('data', exist_ok=True)
            with st.status("Downloading datasets from CERN...", expanded=True) as status:
                for filename, url in datasets.items():
                    st.write(f"Downloading {filename}...")
                    download_dataset(url, os.path.join('data', filename))
                status.update(label="✅ Download complete!", state="complete", expanded=False)
            st.success("Data downloaded successfully! Refreshing...")
            st.rerun()
        st.stop()

# --- Load Data ---
path_to_load = f"data/{selected_file}" if data_source == "Local Storage" else selected_file
is_http_root = path_to_load.startswith("http") and (path_to_load.lower().split('?')[0].endswith('.root') or is_cern_files_proxy) and not is_csv

if is_http_root:
    cache_key = f"streamed_{path_to_load}"
    if cache_key not in st.session_state:
        st.subheader("📡 Live Stream")
        st.session_state[cache_key] = stream_root_data(path_to_load)
    df = st.session_state[cache_key]
else:
    with st.spinner(f"Loading {selected_file}..."):
        df = load_data(path_to_load)

with st.expander("🔍 Raw Data Diagnostic Inspect"):
    st.write(f"Total Events: {len(df)}")
    st.write("Column Names:", df.columns)
    st.dataframe(df.head(5))

# --- Sidebar: Plot Settings & Kinematic Cuts ---
st.sidebar.header("Plot Settings")
bins = st.sidebar.slider("Number of Bins", min_value=10, max_value=500, value=200, step=10)
mass_range = st.sidebar.slider(
    "Invariant mass range [GeV/c²]",
    min_value=float(meta.mass_min - 10), max_value=float(meta.mass_max + 10),
    value=(meta.mass_min, meta.mass_max), step=0.1,
)

# --- Auto Identification Logic ---
if 'particle_name' not in st.session_state:
    st.session_state.particle_name = meta.particle_name
if 'ref_mass' not in st.session_state:
    st.session_state.ref_mass = float(meta.expected_mass)

# Sidebar Controls for Mass & Name (connected to session state)
ref_mass = st.sidebar.number_input(
    "Reference Mass [GeV/c²]",
    value=st.session_state.ref_mass,
    step=0.001,
    format="%.3f",
    help="Position of the red dashed line for PDG mass comparison."
)
particle_name = st.sidebar.text_input("Particle Name", value=st.session_state.particle_name)

# Ensure session state stays in sync if user typed manually
st.session_state.ref_mass = ref_mass
st.session_state.particle_name = particle_name

st.sidebar.header("Kinematic Cuts")
pt_min = st.sidebar.slider("Minimum Muon pT [GeV/c]", 0.0, 50.0, 0.0, 0.5)
eta_max = st.sidebar.slider("Maximum Muon |η|", 0.0, 3.0, 2.4, 0.1)
require_opposite_charge = st.sidebar.checkbox("Require Opposite Charge (Q1 + Q2 = 0)", value=True)

# --- Sidebar: File Inspector ---
st.sidebar.markdown("---")
st.sidebar.header("🛠️ File Tools")
if st.sidebar.checkbox("Show Deep File Inspector"):
    st.subheader("🕵️ Deep ROOT/CSV Inspector")
    path_to_inspect = f"data/{selected_file}" if data_source == "Local Storage" else selected_file
    if is_root:
        struct = get_root_structure(path_to_inspect)
        if "error" in struct:
            st.error(struct["error"])
        else:
            tree_to_inspect = st.selectbox("Select Tree to explore branches", list(struct.keys()))
            if tree_to_inspect:
                details = get_branch_details(path_to_inspect, tree_to_inspect)
                st.write(f"**Found {len(details)} branches in `{tree_to_inspect}`:**")
                st.dataframe(details)
    else:
        st.info("Directly inspecting CSV schema via Polars:")
        st.write(df.schema)

# --- Column Mapping + Invariant Mass ---
df = map_columns(df)

# --- Kinematic Filtering ---
df = apply_kinematic_filters(df, mass_range, pt_min, eta_max, require_opposite_charge)
filtered_df = df.to_pandas()

# Auto-Identify Button (needs filtered_df to find the peak)
if st.sidebar.button("✨ Auto-Identify Particle", help="Detect the primary resonance peak and match against PDG values."):
    with st.spinner("Analyzing mass distribution..."):
        peak = find_primary_peak(filtered_df)
        if peak:
            p_name, p_mass = match_particle(peak)
            st.session_state.particle_name = p_name
            st.session_state.ref_mass = p_mass
            st.toast(f"Detected {p_name} at {p_mass:.3f} GeV!", icon="⚛️")
            st.rerun()
        else:
            st.warning("Could not clearly identify a peak. Try loosening cuts.")

mass_label = "Transverse Mass ($M_T$)" if 'MET' in df.columns else "Invariant Mass"

with st.expander("🔍 Data Diagnostic Inspect", expanded=False):
    st.write(f"**Events Passing Filters:** {len(filtered_df)}")
    if len(filtered_df) > 0:
        st.write("Mapped Columns Preview (GeV):")
        cols_to_show = [c for c in ['pt1', 'pt2', 'eta1', 'eta2', 'Calculated_M'] if c in filtered_df.columns]
        st.dataframe(filtered_df[cols_to_show].head(5))
    else:
        st.warning("⚠️ No events passed your current filters. Try loosening your Kinematic Cuts or widening the Mass Range in the sidebar.")

# --- View Routing ---
view_mode = st.radio("Select View:", ["Mass Histogram", "3D Event Display", "3D Event Animation"])

if view_mode == "Mass Histogram":
    render_mass_histogram(filtered_df, particle_name, ref_mass, mass_range, bins, mass_label)
elif view_mode == "3D Event Display":
    render_3d_event_display(filtered_df, particle_name)
elif view_mode == "3D Event Animation":
    render_3d_animation(filtered_df, particle_name)

# --- Raw Data Preview ---
st.subheader("Raw data preview")
# Show preview directly from Polars
preview_df = df.head(100).to_pandas()
preview_df.columns = [str(c) for c in preview_df.columns]
st.dataframe(preview_df)

render_sidebar_footer()
