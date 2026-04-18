import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from lib.analysis.plots.event_display_3d import _add_cylinder


def render_3d_animation(filtered_df: pd.DataFrame, particle_name: str) -> None:
    """
    Renders a Plotly 3D animation cycling through multiple collision events.

    Each frame updates the muon momentum vectors and the reconstructed parent boost.
    The number of events to animate is controlled by an inline slider (10–100).
    """
    st.subheader("3D Animation of Multiple Events")
    st.markdown("Watch how the kinematics of the collision change event by event natively in Streamlit!")

    if filtered_df.empty:
        st.warning("No events found to animate.")
        return

    anim_events_count = st.slider("Number of Events to Animate", min_value=10, max_value=100, value=30, step=10, key='anim_slider')
    anim_events_count = min(len(filtered_df), anim_events_count)
    st.write(f"Animating the first {anim_events_count} events in the selected mass range...")

    subset_df = filtered_df.head(anim_events_count).copy()
    subset_df['parent_px'] = subset_df['px1'] + subset_df['px2']
    subset_df['parent_py'] = subset_df['py1'] + subset_df['py2']
    subset_df['parent_pz'] = subset_df['pz1'] + subset_df['pz2']

    max_p = max([
        subset_df['px1'].abs().max(), subset_df['py1'].abs().max(), subset_df['pz1'].abs().max(),
        subset_df['px2'].abs().max(), subset_df['py2'].abs().max(), subset_df['pz2'].abs().max(),
        subset_df['parent_px'].abs().max(), subset_df['parent_py'].abs().max(), subset_df['parent_pz'].abs().max(),
    ])
    max_p = max_p if max_p > 0 else 1.0

    fig_anim = go.Figure()
    _add_cylinder(fig_anim, max_p)

    ev0 = subset_df.iloc[0]
    fig_anim.add_trace(go.Scatter3d(
        x=[0, ev0['px1']], y=[0, ev0['py1']], z=[0, ev0['pz1']],
        mode='lines+markers', name='Muon 1',
        line=dict(color='royalblue', width=6), marker=dict(size=4),
    ))
    fig_anim.add_trace(go.Scatter3d(
        x=[0, ev0['px2']], y=[0, ev0['py2']], z=[0, ev0['pz2']],
        mode='lines+markers', name='Muon 2',
        line=dict(color='firebrick', width=6), marker=dict(size=4),
    ))
    fig_anim.add_trace(go.Scatter3d(
        x=[0, ev0['parent_px']], y=[0, ev0['parent_py']], z=[0, ev0['parent_pz']],
        mode='lines+markers', name=f'{particle_name} Boost',
        line=dict(color='darkgreen', width=8, dash='dash'), marker=dict(size=5),
    ))

    frames = [
        go.Frame(
            data=[
                go.Scatter3d(x=[0, ev.px1], y=[0, ev.py1], z=[0, ev.pz1]),
                go.Scatter3d(x=[0, ev.px2], y=[0, ev.py2], z=[0, ev.pz2]),
                go.Scatter3d(x=[0, ev.parent_px], y=[0, ev.parent_py], z=[0, ev.parent_pz]),
            ],
            traces=[1, 2, 3],
            name=f"frame{i}",
        )
        for i, ev in enumerate(subset_df.itertuples(index=False))
    ]
    fig_anim.frames = frames

    fig_anim.update_layout(
        updatemenus=[dict(
            type="buttons", showactive=False,
            y=-0.1, x=0, xanchor="left", yanchor="top", direction="left",
            buttons=[
                dict(label="▶ Play", method="animate",
                     args=[None, dict(frame=dict(duration=800, redraw=True), fromcurrent=True, transition=dict(duration=400))]),
                dict(label="⏸ Pause", method="animate",
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate", transition=dict(duration=0))]),
            ],
        )],
        scene=dict(
            xaxis=dict(title='px [GeV/c]', range=[-max_p, max_p]),
            yaxis=dict(title='py [GeV/c]', range=[-max_p, max_p]),
            zaxis=dict(title='pz [GeV/c]', range=[-max_p, max_p]),
            aspectmode='cube',
        ),
        margin=dict(l=0, r=0, b=0, t=30),
        height=600,
        template='plotly_white',
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99),
    )
    st.plotly_chart(fig_anim, width='stretch')
