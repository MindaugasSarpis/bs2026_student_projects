import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob
import re
from windrose import WindroseAxes

st.set_page_config(layout="wide")

st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem;
        }
    </style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
div[data-baseweb="tab-list"] {
    display: flex;
    justify-content: space-between;
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

plt.rcParams.update({
    "font.size": 7,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.figsize": (3, 3)
})
st.title("Wind Farm Design & Energy Analysis Tool")

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

files = glob.glob("*.csv")

df_list = []

for file in files:
    # Try comma first
    df_temp = pd.read_csv(file, low_memory=False)
    
    # If only one column, it's probably semicolon-delimited
    if df_temp.shape[1] == 1:
        df_temp = pd.read_csv(file, sep=";", low_memory=False)
    
    df_list.append(df_temp)

df = pd.concat(df_list, ignore_index=True)

df = df.rename(columns={"Time and Date": "time"})
df["time"] = pd.to_datetime(df["time"], dayfirst=True, errors="coerce")
df = df.dropna(subset=["time"])

df = df.sort_values("time")
df = df.drop_duplicates(subset="time")

df = df.set_index("time")
df = df.resample("10T").mean()
df = df.reset_index()

# keep a copy with all height columns for later (turbine comparison)
df_full = df.copy()

# ---------------------------------------------------------
# EXTRACT HEIGHTS FROM COLUMNS
# ---------------------------------------------------------

height_cols = [
    c for c in df.columns
    if "Horizontal Wind Speed (m/s) at" in c
]

heights = sorted({
    int(re.search(r"(\d+)m", c).group(1))
    for c in height_cols
})

# ---------------------------------------------------------
# CONTROLS
# ---------------------------------------------------------

turbines = {
    "Vestas V164 8MW": {"rated_power":8000,"cut_in":3,"rated_speed":12,"cut_out":25,"rotor_diameter":164, "hub_height":150},
    "Vestas V150 6MW": {"rated_power":6000,"cut_in":3,"rated_speed":11.5,"cut_out":25,"rotor_diameter":150, "hub_height":120},
    "Siemens SG 6.0-154": {"rated_power":6000,"cut_in":3,"rated_speed":12,"cut_out":25,"rotor_diameter":154, "hub_height":150},
    "Nordex N149 5MW": {"rated_power":5000,"cut_in":3,"rated_speed":11.5,"cut_out":25,"rotor_diameter":149, "hub_height":125},
    "GE Haliade-X 12MW": {"rated_power":12000,"cut_in":3,"rated_speed":11,"cut_out":25,"rotor_diameter":220, "hub_height":150}
}

c1, c2 = st.columns(2)

with c1:
    turbine_name = st.selectbox("Choose a wind turbine model:", list(turbines.keys()))
    # store selected turbine in session_state for later tabs
    st.session_state["selected_turbine"] = turbine_name

with c2:
    height = st.selectbox("Choose measurement height (m):", heights)

turbine = turbines[turbine_name]
rotor_diameter = turbine["rotor_diameter"]

# ---------------------------------------------------------
# SELECT HEIGHT
# ---------------------------------------------------------

wind_column = f"Horizontal Wind Speed (m/s) at {height}m"
direction_column = f"Wind Direction (deg) at {height}m"

df["wind"] = pd.to_numeric(df[wind_column], errors="coerce")
df["direction"] = pd.to_numeric(df[direction_column], errors="coerce")

# Remove invalid direction values
df.loc[df["direction"] > 360, "direction"] = np.nan
df.loc[df["direction"] < 0, "direction"] = np.nan
df.loc[df["wind"] < 0.5, "direction"] = np.nan


df = df.dropna(subset=["wind","direction"])

df.loc[df["wind"] > 100, "wind"] = np.nan
df = df.dropna(subset=["wind"])

# ---------------------------------------------------------
# TIME FILTER
# ---------------------------------------------------------

st.sidebar.header("Filter Data")

min_date = df["time"].min()
max_date = df["time"].max()

start_date, end_date = st.sidebar.date_input(
    "Select time range:",
    [min_date, max_date],
    min_value=min_date,
    max_value=max_date
)

# Apply filter to main df
df = df[(df["time"] >= pd.to_datetime(start_date)) & 
        (df["time"] <= pd.to_datetime(end_date))]

# Apply same filter to df_full for later use (turbine comparison)
df_full = df_full[(df_full["time"] >= pd.to_datetime(start_date)) &
                  (df_full["time"] <= pd.to_datetime(end_date))]

# ---------------------------------------------------------
# CALCULATIONS
# ---------------------------------------------------------

avg_wind = df["wind"].mean()
max_wind = df["wind"].max()

def turbine_power(v, turbine):
    if v < turbine["cut_in"]:
        return 0
    elif v < turbine["rated_speed"]:
        return turbine["rated_power"] * ((v - turbine["cut_in"]) / (turbine["rated_speed"] - turbine["cut_in"]))**3
    elif v < turbine["cut_out"]:
        return turbine["rated_power"]
    else:
        return 0

def wake_loss_factor(spacing_d):
    if spacing_d < 4:
        return 0.20
    elif spacing_d < 6:
        return 0.12
    elif spacing_d < 8:
        return 0.08
    elif spacing_d < 10:
        return 0.05
    else:
        return 0.03

df["power_kw"] = df["wind"].apply(lambda v: turbine_power(v, turbine))

time_hours = 10 / 60
df["energy_kwh"] = df["power_kw"] * time_hours

total_energy = df["energy_kwh"].sum() / 1000  # MWh

hours_measured = len(df) * time_hours
annual_energy = total_energy * (8760 / hours_measured)

capacity_factor = df["energy_kwh"].sum() / (turbine["rated_power"] * hours_measured)

df["year_month"] = df["time"].dt.to_period("M")

monthly_avg = df.groupby("year_month")["wind"].mean()
monthly_energy = df.groupby("year_month")["energy_kwh"].sum() / 1000

# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "Overview",
    "Monthly Analysis",
    "Wind Distribution",
    "Wind Direction",
    "Turbine Performance",
    "Turbine Comparison",
    "Wind Farm Design",
    "Energy Yield Assessment"
])

# ---------------------------------------------------------
# TAB 1: OVERVIEW
# ---------------------------------------------------------

with tab1:

    col1, col2 = st.columns([1,2])

    with col1:
        st.subheader("Overview")

        st.write("""
        This section provides a general summary of the wind resource 
        at the selected height and its suitability for energy production.
        
        Key metrics include average wind speed, extreme values, 
        and estimated energy output using the selected turbine model.
        """)
        st.info("Note: All energy results in this section are calculated for a single turbine. Annual energy is estimated from measured data and scaled to a full year.")

        st.markdown("### Key Results")

        st.write(f"• Average wind speed: **{avg_wind:.2f} m/s**")
        st.write(f"• Maximum wind speed: **{max_wind:.2f} m/s**")
        st.write(f"• Energy (measured): **{total_energy:.0f} MWh**")
        st.write(f"• Estimated annual: **{annual_energy:.0f} MWh**")
        st.write(f"• Capacity factor: **{capacity_factor*100:.1f}%**")

        st.markdown("""
        **Interpretation:**
        - >9 m/s → Excellent offshore wind resource  
        - Capacity factor >40% → Very strong project potential  
        """)

    with col2:
        fig, ax = plt.subplots(figsize=(6,3))
        ax.plot(df["time"], df["wind"])

        ax.set_title(f"Wind Speed at {height} m")
        ax.set_xlabel("Time (date)")
        ax.set_ylabel("Wind Speed (m/s)")

        st.pyplot(fig)

# ---------------------------------------------------------
# TAB 2: MONTHLY ANALYSIS
# ---------------------------------------------------------

with tab2:

    col1, col2 = st.columns([1,2])

    with col1:
        st.subheader("Monthly Analysis")

        st.write("""
        This section shows how wind conditions and energy production 
        vary throughout the year.

        Seasonal variation is critical for estimating revenue stability 
        and grid integration.
        """)
        st.info("Note: Monthly energy values represent production from one turbine only. Some months might contain incomplete datasets.")

        st.markdown("### Monthly Energy (MWh)")

        for month, value in monthly_energy.items():
            st.write(f"• {month}: **{value:.0f} MWh**")

        st.markdown("""
        **Interpretation:**
        - Higher winter production is expected offshore  
        - Large variation may impact financial planning  
        """)

    with col2:
        fig, ax = plt.subplots(figsize=(6,3))

        monthly_energy.plot(kind="barh", ax=ax)

        ax.set_title("Monthly Energy Production")
        ax.set_ylabel("Time (date)")
        ax.set_xlabel("Energy (MWh)")

        st.pyplot(fig)

# ---------------------------------------------------------
# TAB 3: WIND DISTRIBUTION
# ---------------------------------------------------------

with tab3:

    col1, col2 = st.columns([1,2])

    with col1:
        st.subheader("Wind Speed Distribution")

        st.write("""
        This histogram shows how frequently different wind speeds occur.

        It is critical because turbine power output depends strongly 
        on wind speed distribution, not just averages.
        """)

        st.markdown(f"""
        **Key Insight:**
        - Most frequent wind speeds define energy production
        - Speeds near rated speed (~{turbine['rated_speed']} m/s) are ideal
        """)

    with col2:
        fig, ax = plt.subplots(figsize=(6,3))

        ax.hist(df["wind"], bins=30, density=True)

        ax.set_title("Wind Speed Distribution")
        ax.set_xlabel("Wind Speed (m/s)")
        ax.set_ylabel("Probability density")

        st.pyplot(fig)

# ---------------------------------------------------------
# TAB 4: WIND ROSE
# ---------------------------------------------------------
def deg_to_compass(deg):
    directions = [
        "N", "NNE", "NE", "ENE",
        "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW",
        "W", "WNW", "NW", "NNW"
    ]
    idx = round(deg / 22.5) % 16
    return directions[idx]

with tab4:

    col1, col2 = st.columns([1,1])

    with col1:
        st.subheader("Wind Direction Analysis")

        st.write("""
        The wind rose shows how wind speed and direction are distributed.

        It is essential for turbine layout and orientation in a wind farm.
        """)

        bins = np.arange(0, 361, 30)
        df["dir_bin"] = pd.cut(df["direction"], bins, include_lowest=True)

        dominant_bin = df["dir_bin"].value_counts().idxmax()
        dominant_dir = dominant_bin.mid
        compass_dir = deg_to_compass(dominant_dir)

        st.markdown(f"""
        **Key Insight:**
        - Dominant wind direction: ~{dominant_dir:.0f}° ({compass_dir})
        - Turbines should face this direction for maximum efficiency
        """)

        st.markdown("""
        **How to read:**
        - Each “arm” represents a wind direction  
        - The length of each segment shows how frequently wind comes from that direction  
        - Concentric circles indicate percentage frequency (how often wind occurs)  
        - Colors represent different wind speed ranges  
        """)

    with col2:
        fig = plt.figure(figsize=(3.5,3.5))

        ax = WindroseAxes.from_ax(fig=fig)

        ax.bar(
            df["direction"],
            df["wind"],
            bins=[0,4,8,12,16,20,25],
            normed=True,
            opening=0.8,
            edgecolor='white'
        )
        ax.tick_params(labelsize=10)

        ax.set_rlabel_position(225)

        ax.set_title("Wind Rose", fontsize=10)
    
        ax.set_legend(
            title="Wind speed, m/s",
            fontsize=7,
            title_fontsize=8,
            loc="lower left",
            bbox_to_anchor=(1.0, -0.1)
        )

        st.pyplot(fig)

# ---------------------------------------------------------
# TAB 5: TURBINE PERFORMANCE
# ---------------------------------------------------------

with tab5:

    col1, col2 = st.columns([1,2])

    with col1:
        st.subheader("Turbine Power Curve")

        st.write("""
        The power curve shows how much electricity the turbine produces 
        at different wind speeds.

        It is one of the most important characteristics of a wind turbine.
        """)

        st.markdown(f"""
        **Key points:**
        - Cut-in speed: {turbine['cut_in']} m/s  
        - Rated speed: {turbine['rated_speed']} m/s  
        - Cut-out speed: {turbine['cut_out']} m/s  
        """)

        st.write(f"Rotor diameter: {rotor_diameter} m")

    with col2:
        speeds = list(range(0, 30))
        powers = [turbine_power(v, turbine) for v in speeds]

        fig, ax = plt.subplots(figsize=(5.5,2.5))
        ax.plot(speeds, powers)

        ax.set_title("Power Curve")
        ax.set_xlabel("Wind Speed (m/s)")
        ax.set_ylabel("Power (kW)")

        st.pyplot(fig)

# ---------------------------------------------------------
# TAB 6: TURBINE COMPARISON
# ---------------------------------------------------------
with tab6:

    st.subheader("Turbine Comparison at Selected Site")

    st.write("""
    This section compares different turbine models under the same wind conditions.

    Each turbine is evaluated using wind data from the **measurement height closest to its hub height**, 
    ensuring a more realistic representation of operating conditions.

    The results show annual energy production and capacity factor for each turbine.
    """)

    col1, col2 = st.columns([1, 1.25])

    results = []

    for name, turb in turbines.items():

        hub = turb["hub_height"]
        selected_height = min(heights, key=lambda h: abs(h - hub))

        wind_column_t = f"Horizontal Wind Speed (m/s) at {selected_height}m"

        if wind_column_t not in df_full.columns:
            continue

        df_t = df_full[["time", wind_column_t]].copy()
        df_t["wind"] = pd.to_numeric(df_t[wind_column_t], errors="coerce")
        df_t = df_t.dropna(subset=["wind"])
        df_t.loc[df_t["wind"] > 100, "wind"] = np.nan
        df_t = df_t.dropna(subset=["wind"])

        power = df_t["wind"].apply(lambda v: turbine_power(v, turb))
        energy_kwh = power * (10 / 60)

        total_energy_t = energy_kwh.sum() / 1000  # MWh
        hours_measured_t = len(df_t) * (10 / 60)

        if hours_measured_t == 0:
            continue

        annual_energy_t = total_energy_t * (8760 / hours_measured_t)

        capacity_factor_t = (
            energy_kwh.sum() / (turb["rated_power"] * hours_measured_t)
        )

        results.append({
            "Turbine": name,
            "Hub Height (m)": hub,
            "Selected Wind Height (m)": selected_height,
            "Annual Energy (MWh)": annual_energy_t,
            "Capacity Factor (%)": capacity_factor_t * 100
        })

    results_df = pd.DataFrame(results)
    

    if not results_df.empty:
        results_df = results_df.sort_values(
            "Annual Energy (MWh)",
            ascending=False
        )

    with col1:

        st.markdown("### Results Table")
        
        if results_df.empty:
            st.write("No valid results to display (check data columns and time range).")
        else:
            st.dataframe(results_df)

            best = results_df.iloc[0]

            st.markdown("### Interpretation")

            st.write(f"""
            The best performing turbine at this site is the **{best['Turbine']}**.

            It achieves the highest annual energy output due to:
            - Better matching between hub height ({best['Hub Height (m)']} m) and available wind measurement height ({best['Selected Wind Height (m)']} m)
            - Its rated power and power curve characteristics in the observed wind speed range

            ### Key insight:
            Turbines are sensitive to wind speed variations with height.
            Even small differences in hub height can significantly affect energy yield.
            """)

    with col2:

        if not results_df.empty:
            fig, ax = plt.subplots(figsize=(4, 3))

            ax.barh(
                results_df["Turbine"],
                results_df["Annual Energy (MWh)"]
            )

            ax.set_title("Annual Energy Comparison")
            ax.set_xlabel("MWh")      # horizontal chart → x‑axis is the value
            ax.set_ylabel("")         # optional: remove y‑axis label

            plt.tight_layout()
            st.pyplot(fig)

            st.caption("""
            Energy output comparison across turbine models using height-adjusted wind data.
            Each turbine uses the closest available measurement height to its hub height.
            """)
        else:
            st.write("No comparison plot available (no valid turbine results).")

# ---------------------------------------------------------
# TAB 7: WIND FARM DESIGN
# ---------------------------------------------------------
with tab7:

    col1, col2 = st.columns([1,2])

    with col1:
        st.subheader("Wind Farm Layout")
        st.markdown("""
        **Model assumptions:**
        - Constant thrust coefficient (CT = 0.6)
        - Linear wake expansion (Jensen wake model, simplified)
        - Uniform offshore wind conditions
        - Wake deficit capped to avoid unrealistic wind speed reductions
        - No electrical or mechanical losses included
        """)

        num_turbines = st.slider("Number of turbines", 1, 55, 20)
        spacing_downwind = st.slider("Downwind spacing (D)", 3.0, 12.0, 7.0)
        spacing_crosswind = st.slider("Crosswind spacing (D)", 3.0, 12.0, 5.0)

        st.session_state["num_turbines"] = num_turbines
        st.session_state["wake_loss"] = wake_loss_factor(spacing_downwind)

        spacing_downwind_m = spacing_downwind * rotor_diameter
        spacing_crosswind_m = spacing_crosswind * rotor_diameter

        st.markdown("### Spacing")
        st.write(f"• Downwind: {spacing_downwind_m:.0f} m")
        st.write(f"• Crosswind: {spacing_crosswind_m:.0f} m")

        st.markdown("---")

        show_wake_effect = st.checkbox(
            "Highlight wake-affected turbines",
            True
        )

        st.caption("Red circles indicate turbines significantly affected by wake effects.")

        bins = np.arange(0, 361, 30)
        df["dir_bin"] = pd.cut(df["direction"], bins, include_lowest=True)
        dir_freq = df["dir_bin"].value_counts(normalize=True)

        dominant_bin = dir_freq.idxmax()
        wind_dir = dominant_bin.mid
        theta = np.radians(wind_dir)
    
        st.markdown("### Wind Direction")

        fig_compass, ax_compass = plt.subplots(figsize=(1.2,1.2))

        circle = plt.Circle((0,0), 0.8, fill=False, linewidth=0.6)
        ax_compass.add_patch(circle)

        ax_compass.plot([0,0], [-0.8,0.8], color="gray", linewidth=0.5)
        ax_compass.plot([-0.8,0.8], [0,0], color="gray", linewidth=0.5)

        ax_compass.text(0, 1, "N", ha='center', fontsize=6)
        ax_compass.text(1, 0, "E", va='center', fontsize=6)
        ax_compass.text(0, -1.2, "S", ha='center', fontsize=6)
        ax_compass.text(-1.2, 0, "W", va='center', fontsize=6)

        ax_compass.arrow(
            0, 0,
            0.5*np.cos(theta),
            0.5*np.sin(theta),
            head_width=0.12,
            color="black"
        )

        ax_compass.set_xlim(-1.2,1.2)
        ax_compass.set_ylim(-1.2,1.2)
        ax_compass.axis('off')

        st.pyplot(fig_compass)

        st.caption(
            "Wind farm performance is evaluated by weighting turbine output across all wind directions based on their observed frequency."
        )

    with col2:

        cols = int(np.sqrt(num_turbines))
        rows = int(np.ceil(num_turbines / cols))

        dw_vec = np.array([np.cos(theta), np.sin(theta)])
        cw_vec = np.array([-np.sin(theta), np.cos(theta)])

        x, y = [], []

        for i in range(rows):
            for j in range(cols):
                if len(x) < num_turbines:

                    stagger = 0.5 * spacing_crosswind_m if i % 2 == 1 else 0

                    pos = (
                        i * spacing_downwind_m * dw_vec +
                        (j * spacing_crosswind_m + stagger) * cw_vec
                    )

                    x.append(pos[0])
                    y.append(pos[1])

        x = np.array(x)
        y = np.array(y)

        x -= x.min()
        y -= y.min()

        CT = 0.6
        k_wake = 0.075
        R = rotor_diameter / 2

        effective_wind_total = np.zeros(len(x))
        total_weight = 0

        for dir_bin, weight in dir_freq.items():

            if weight == 0:
                continue

            theta_i = np.radians(dir_bin.mid)

            dw_vec_i = np.array([np.cos(theta_i), np.sin(theta_i)])
            cw_vec_i = np.array([-np.sin(theta_i), np.cos(theta_i)])

            base_wind_i = df[df["dir_bin"] == dir_bin]["wind"].mean()

            if np.isnan(base_wind_i):
                continue

            effective_wind_dir = np.full(len(x), base_wind_i)

            for i in range(len(x)):

                deficit_sq_sum = 0

                for j in range(len(x)):
                    if i == j:
                        continue

                    dx = x[i] - x[j]
                    dy = y[i] - y[j]

                    x_down = dx * dw_vec_i[0] + dy * dw_vec_i[1]
                    y_cross = abs(dx * cw_vec_i[0] + dy * cw_vec_i[1])

                    if x_down <= 0:
                        continue

                    wake_radius = R + k_wake * x_down

                    if y_cross <= wake_radius:
                        deficit = (1 - np.sqrt(1 - CT)) * (R / wake_radius) ** 2
                        deficit_sq_sum += (0.7 * deficit) ** 2

                total_deficit = min(np.sqrt(deficit_sq_sum), 0.6)
                effective_wind_dir[i] = max(0, base_wind_i * (1 - total_deficit))

            effective_wind_total += weight * effective_wind_dir
            total_weight += weight

        effective_wind = effective_wind_total / max(total_weight, 1e-6)

        norm = (effective_wind - effective_wind.min()) / (
            effective_wind.max() - effective_wind.min() + 1e-6
        )

        fig, ax = plt.subplots(figsize=(4,4))

        scatter = ax.scatter(
            x, y,
            c=norm,
            cmap="viridis",
            s=30
        )

        threshold = np.percentile(effective_wind, 25)
        affected_count = np.sum(effective_wind < threshold)

        if show_wake_effect:
            for xi, yi, w in zip(x, y, effective_wind):
                if w < threshold:
                    ax.scatter(xi, yi, edgecolor='red', facecolor='none', s=70, linewidth=1)

        arrow_length = rotor_diameter * 1.2

        for xi, yi in zip(x, y):
            ax.arrow(
                xi, yi,
                -arrow_length * dw_vec[0],
                -arrow_length * dw_vec[1],
                head_width=rotor_diameter * 0.2,
                color="black",
                alpha=0.5
            )

        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label("Effective wind speed", fontsize=8)
        cbar.ax.tick_params(labelsize=7)

        ax.set_xlabel("Distance (m)", fontsize=8)
        ax.set_ylabel("Distance (m)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.set_aspect('equal')

        st.pyplot(fig)

        avg_all = np.mean(effective_wind)
        avg_wake = np.mean(effective_wind[effective_wind < threshold]) if affected_count > 0 else avg_all
        loss_percent = (1 - avg_wake / avg_all) * 100 if avg_all > 0 else 0

        st.markdown(
            f"In this layout, {affected_count} out of {num_turbines} turbines are significantly affected by wake effects, "
            f"with an average wind speed reduction of {loss_percent:.1f}%."
        )
        st.caption(
            "Wake losses occur when downstream turbines operate in reduced wind speeds caused by upstream turbines."
        )

# ---------------------------------------------------------
# TAB 8: ENERGY YIELD & UNCERTAINTY (P50 / P75 / P90)
# ---------------------------------------------------------

with tab8:

    from scipy.stats import norm

    col1, col2 = st.columns([1,1.25])

    with col1:
        st.subheader("Energy Yield Assessment")

        num_turbines = st.session_state.get("num_turbines", 20)
        wake_loss = st.session_state.get("wake_loss", 0.1)
        turbine_name = st.session_state.get("selected_turbine", "Vestas V164 8MW")

        uncertainty = st.slider(
            "Total uncertainty (%)",
            5, 15, 10
        ) / 100

        energy_per_turbine = annual_energy  # MWh/year

        total_energy_farm = energy_per_turbine * num_turbines * (1 - wake_loss)

        energy_p50 = total_energy_farm
        energy_p75 = energy_p50 * (1 - 0.5 * uncertainty)
        energy_p90 = energy_p50 * (1 - uncertainty)

        st.markdown("### Wind Farm Production")

        st.write(f"• Turbine model: **{turbine_name}**")
        st.write(f"• Number of turbines: **{num_turbines}**")
        st.write(f"• Wake loss applied: **{wake_loss*100:.1f}%**")

        st.markdown("### Energy Yield Estimates")

        st.write(f"• P50 (expected): **{energy_p50:,.0f} MWh/year**")
        st.write(f"• P75: **{energy_p75:,.0f} MWh/year**")
        st.write(f"• P90: **{energy_p90:,.0f} MWh/year**")

        st.markdown("### Accuracy & Methodology")

        st.info("""
        These P50, P75, and P90 values are simplified estimates based on measured wind data 
        and an assumed total uncertainty range.

        **Accuracy level:**
        - Suitable for early-stage assessment (screening / concept level)
        - Not suitable for investment-grade (bankable) decisions

        This model does NOT include several critical components required for accurate yield prediction:
        
        • Long-term wind climate correction (MCP analysis)  
        • Interannual wind variability (multi-year reference data)  
        • Detailed wake modeling across the full wind farm layout  
        • Turbine availability and operational downtime  
        • Electrical and grid losses  
        • Environmental effects (icing, degradation, curtailment)  

        Therefore, results here should be interpreted as indicative, not definitive.
        """)

    with col2:
        
        mean = energy_p50
        std_dev = mean * uncertainty

        x_vals = np.linspace(mean * 0.7, mean * 1.2, 200)
        y_vals = norm.pdf(x_vals, mean, std_dev)

        fig, ax = plt.subplots(figsize=(6,4))

        ax.plot(x_vals, y_vals)

        ax.axvline(energy_p50, linestyle="-", linewidth=2, label="P50")
        ax.axvline(energy_p75, linestyle="--", linewidth=2, label="P75")
        ax.axvline(energy_p90, linestyle=":", linewidth=2, label="P90")

        ax.set_xlabel("Annual Energy Production (MWh)")
        ax.set_ylabel("Probability density")
        ax.set_title("Energy Yield Uncertainty")

        ax.legend()

        st.pyplot(fig)

        st.markdown("""
        **How to read this graph:**

        - The curve represents possible annual energy outcomes based on uncertainty  
        - **P50** is the expected (most likely) production  
        - **P75 and P90** represent increasingly conservative estimates  

        **Uncertainty slider:**
        - Controls how “spread out” the possible outcomes are  
        - Higher uncertainty → larger gap between P50 and P90  
        - Typical offshore projects range between **8–12% uncertainty**  

        This simplified model assumes a normal distribution of wind variability 
        and does not include full long-term corrections.
        """)

