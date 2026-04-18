import streamlit as st
import os
from pathlib import Path


def get_shared_styles() -> str:
    """Returns the CSS string for the dashboard layout tweaks."""
    return """
        <style>
        /* Base styles */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Sidebar navigation spacing and hover enhancements */
        [data-testid="stSidebarNav"] ul {
            padding-top: 1rem;
        }

        [data-testid="stSidebarNav"] li {
            margin-bottom: 5px;
            border-radius: 8px;
            transition: all 0.3s ease;
        }

        [data-testid="stSidebarNav"] li:hover {
            background-color: rgba(0, 212, 255, 0.1);
        }

        [data-testid="stSidebarNav"] .st-eb {
            color: #ffffff;
            font-weight: 600;
        }

        /* Titles and Headers - Fine-tuning weight and spacing */
        h1 {
            font-weight: 800 !important;
            letter-spacing: -0.02em;
        }

        h2, h3 {
            font-weight: 600 !important;
        }

        /* Buttons and Interactive Elements */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: transform 0.1s ease;
        }

        .stButton>button:active {
            transform: scale(0.98);
        }
        </style>
    """


def apply_branding() -> None:
    """Injects shared CSS. Call once at the top of each page."""
    st.markdown(get_shared_styles(), unsafe_allow_html=True)


def render_sidebar_footer() -> None:
    """
    Renders logo, system status, and footer in the sidebar.
    Call at the END of each page so page controls appear above these elements.
    """
    root_dir = Path(__file__).parent.parent
    logo_path = root_dir / "assets" / "logo.png"

    with st.sidebar:
        st.markdown("---")

        if logo_path.exists():
            st.image(str(logo_path), width='stretch')
        else:
            st.title("⚛️ CERN Explorer")

        st.caption("🛰️ System Status: **Optimal**")
        st.caption("📦 Cache Health: **Ready**")

        st.markdown("""
            <div style='text-align: center; opacity: 0.7; font-size: 0.8em; margin-top: 0.5rem;'>
                🚀 Developed by <br>
                <a href='https://github.com/VytasMule' target='_blank' style='color: #00d4ff; text-decoration: none; font-weight: 800;'>Vytas Mulevicius</a> <br>
                <p style='margin-top: 5px;'>© 2026 CERN Open Data </p>
            </div>
        """, unsafe_allow_html=True)
