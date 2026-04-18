import pandas as pd
import streamlit as st
import numpy as np
import plotly.graph_objects as go


def render_3d_event_display(filtered_df: pd.DataFrame, particle_name: str) -> None:
    """
    Renders a single collision event as 3D momentum vectors in a Plotly scene.
    Supports both Dimuon (2 particle) and W-like (1 lepton + MET) topologies.
    """
    st.subheader("3D Momentum Visualization")

    if filtered_df.empty:
        st.warning("No events found in this mass range.")
        return

    is_w_boson = 'MET' in filtered_df.columns

    if is_w_boson:
        st.markdown("View the 3D momentum of the **lepton** (Blue) balanced by **Missing Transverse Energy** (Magenta).")
    else:
        st.markdown("View the 3D momentum vectors ($p_x, p_y, p_z$) of the **two muons** for a single event.")

    event_idx = st.slider("Select Event Index from Filtered Data", 0, len(filtered_df) - 1, 0, key='event_slider')
    event = filtered_df.iloc[event_idx]

    fig3d = go.Figure()

    if is_w_boson:
        # --- Single Lepton + MET Mode ---
        max_p = max(abs(event['px']), abs(event['py']), abs(event['pz']), abs(event['pxMET']), abs(event['pyMET']))
        max_p = max_p if max_p > 0 else 1.0
        _add_cylinder(fig3d, max_p)

        # Lepton vector
        fig3d.add_trace(go.Scatter3d(
            x=[0, event['px']], y=[0, event['py']], z=[0, event['pz']],
            mode='lines+markers', name='Lepton',
            line=dict(color='royalblue', width=6), marker=dict(size=4, color='royalblue'),
        ))
        # MET vector (pz is always 0 for MET)
        fig3d.add_trace(go.Scatter3d(
            x=[0, event['pxMET']], y=[0, event['pyMET']], z=[0, 0],
            mode='lines+markers', name='MET (Missing E_T)',
            line=dict(color='magenta', width=6, dash='dot'), marker=dict(size=4, color='magenta'),
        ))
    else:
        # --- Dimuon Mode ---
        max_p = max(
            abs(event['px1']), abs(event['py1']), abs(event['pz1']),
            abs(event['px2']), abs(event['py2']), abs(event['pz2']),
        )
        max_p = max_p if max_p > 0 else 1.0
        _add_cylinder(fig3d, max_p)

        fig3d.add_trace(go.Scatter3d(
            x=[0, event['px1']], y=[0, event['py1']], z=[0, event['pz1']],
            mode='lines+markers', name='Muon 1',
            line=dict(color='royalblue', width=6), marker=dict(size=4, color='royalblue'),
        ))
        fig3d.add_trace(go.Scatter3d(
            x=[0, event['px2']], y=[0, event['py2']], z=[0, event['pz2']],
            mode='lines+markers', name='Muon 2',
            line=dict(color='firebrick', width=6), marker=dict(size=4, color='firebrick'),
        ))

        parent_px = event['px1'] + event['px2']
        parent_py = event['py1'] + event['py2']
        parent_pz = event['pz1'] + event['pz2']

        fig3d.add_trace(go.Scatter3d(
            x=[0, parent_px], y=[0, parent_py], z=[0, parent_pz],
            mode='lines+markers', name=f'{particle_name} Boost Vector',
            line=dict(color='darkgreen', width=8, dash='dash'), marker=dict(size=5, color='darkgreen'),
        ))
        max_p = max(max_p, abs(parent_px), abs(parent_py), abs(parent_pz))

    fig3d.update_layout(
        scene=dict(
            xaxis=dict(title='px [GeV/c]', range=[-max_p, max_p]),
            yaxis=dict(title='py [GeV/c]', range=[-max_p, max_p]),
            zaxis=dict(title='pz [GeV/c]', range=[-max_p, max_p]),
            aspectmode='cube',
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        height=600,
        template='plotly_white',
    )
    st.plotly_chart(fig3d, width='stretch')

    st.markdown("### Physics Analytics")
    col1, col2, col3 = st.columns(3)
    with col1:
        label = "Transverse Mass ($M_T$)" if is_w_boson else "Calculated Mass"
        st.metric(label, f"{event['Calculated_M']:.3f} GeV/c²")
    
    if is_w_boson:
        with col2:
            st.metric("Lepton $p_T$", f"{event['pt']:.2f} GeV/c")
        with col3:
            st.metric("MET Magnitude", f"{event['MET']:.2f} GeV")
    else:
        with col2:
            p1_mag = np.sqrt(event['px1']**2 + event['py1']**2 + event['pz1']**2)
            p2_mag = np.sqrt(event['px2']**2 + event['py2']**2 + event['pz2']**2)
            dot = event['px1']*event['px2'] + event['py1']*event['py2'] + event['pz1']*event['pz2']
            cos_theta = np.clip(dot / (p1_mag * p2_mag), -1.0, 1.0)
            st.metric("3D Opening Angle (θ)", f"{np.degrees(np.arccos(cos_theta)):.1f}°")
        with col3:
            pt_parent = np.sqrt(parent_px**2 + parent_py**2)
            st.metric("Pair Transverse Momentum ($p_T$)", f"{pt_parent:.2f} GeV/c")

    if is_w_boson:
        st.info("💡 **How to interpret:** The Blue vector is the observed lepton. The Magenta dotted vector is the Missing Transverse Energy (MET), indicating unobserved particles (neutrinos). In a W-boson decay, these two vectors should roughly balance each other in the transverse plane.")
    else:
        st.info("💡 **How to interpret:** The green dashed vector shows the momentum of the parent particle before decay (boost). The grey cylinder is a conceptual representation of the CMS inner detector. If the Pair $p_T$ is large, the rest of the event must have a large recoiling transverse momentum (origin of MET signatures).")


def _add_cylinder(fig: go.Figure, max_p: float) -> None:
    theta = np.linspace(0, 2 * np.pi, 50)
    z_cyl = np.linspace(-max_p * 1.2, max_p * 1.2, 2)
    theta_grid, z_grid = np.meshgrid(theta, z_cyl)
    x_cyl = (max_p * 0.8) * np.cos(theta_grid)
    y_cyl = (max_p * 0.8) * np.sin(theta_grid)
    fig.add_trace(go.Surface(
        x=x_cyl, y=y_cyl, z=z_grid,
        opacity=0.1, colorscale=[[0, 'gray'], [1, 'gray']],
        showscale=False, hoverinfo='skip', name='CMS Barrel (Conceptual)',
    ))
