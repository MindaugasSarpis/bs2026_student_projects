import streamlit as st
import os
from scripts.davinci_macros.make_ntuple import generate_davinci_config
from lib.ui_utils import apply_branding, render_sidebar_footer

st.set_page_config(page_title="CERN Explorer | Macros", page_icon="⚛️", layout="wide")

# Apply unified enterprise branding
apply_branding()

st.title("📝 LHCb Macro Generator")
st.markdown("""
This tool generates **DaVinci/Gaudi** configuration scripts (macros) required to process raw DST/ROOT files 
using the official LHCb software stack.

Export these scripts to run them on the CERN GRID or your local cluster.
""")

# Scan for files
available_files = sorted([f for f in os.listdir('data') if f.endswith(('.root', '.dst'))])

if not available_files:
    st.warning("📂 No datasets found. Go to the **Explorer** page to download data!")
    st.stop()

col1, col2 = st.columns([1, 2])

with col1:
    st.header("Job Configuration")
    selected_file = st.selectbox("Select Target Dataset", available_files)
    particle = st.text_input("Target Resonance (e.g. Jpsi, Z, Y)", value="Jpsi")
    stripping_line = st.text_input("Stripping Line Name", value="FullDSTDiMuonJpsiLine")
    stream = st.text_input("Data Stream", value="Dimuon")
    year = st.selectbox("Data Year", ["2011", "2012", "2015", "2016", "2017", "2018"], index=1)

    dataset_path = f"data/{selected_file}"
    
    macro_code = generate_davinci_config(
        dataset_path=dataset_path,
        particle=particle,
        stripping_line=stripping_line,
        stream=stream,
        year=year
    )

with col2:
    st.header("Generated Macro")
    st.caption(f"Config generated for: `{selected_file}`")
    st.code(macro_code, language="python")
    
    st.download_button(
        label="📥 Download Macro (.py)",
        data=macro_code,
        file_name=f"dv_{particle}_{year}.py",
        mime="text/x-python"
    )

st.info("💡 **Tip:** To find the exact Stripping Line name, run the `find_stripping_lines.py` script from the `scripts/davinci_macros/` directory on a CERN login node.")

render_sidebar_footer()
