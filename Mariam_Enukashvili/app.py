import pandas as pd
import streamlit as st
import altair as alt

st.set_page_config(page_title="Startup Market Analyzer", layout="wide")

st.markdown("""
    <style>
    .main {
        background-color: #f7f9fc;
    }

    h1 {
        color: #1f3c88;
        font-weight: 800;
    }

    h2, h3 {
        color: #173f5f;
    }

    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dbe4f0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }

    div[data-testid="stDataFrame"] {
        background-color: white;
        border-radius: 10px;
    }

    .custom-box {
        background-color: white;
        padding: 18px;
        border-radius: 14px;
        border: 1px solid #dbe4f0;
        margin-bottom: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# Load and prepare data
# -----------------------------
file_path = "data/raw/startups.csv"
df = pd.read_csv(file_path)

# Convert numeric columns safely
numeric_columns = [
    "Founded Year",
    "Total Funding ($M)",
    "Number of Employees",
    "Annual Revenue ($M)",
    "Valuation ($B)",
    "Success Score",
    "Customer Base (Millions)",
    "Social Media Followers"
]

for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# Remove rows with missing key columns where needed
df["Country"] = df["Country"].astype(str)
df["Industry"] = df["Industry"].astype(str)
df["Funding Stage"] = df["Funding Stage"].astype(str)

# -----------------------------
# Title section
# -----------------------------
st.markdown("""
<div class="custom-box">
    <h1>Startup Market Analyzer</h1>
    <p style="font-size:18px; color:#4a5568;">
        This dashboard explores global startup trends across countries, industries, funding, valuation, and performance.
    </p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# Filters
# -----------------------------
st.subheader("Filters")

filter_col1, filter_col2, filter_col3 = st.columns(3)

selected_country = filter_col1.selectbox(
    "Select a country",
    ["All"] + sorted(df["Country"].dropna().unique().tolist())
)

selected_industry = filter_col2.selectbox(
    "Select an industry",
    ["All"] + sorted(df["Industry"].dropna().unique().tolist())
)

selected_stage = filter_col3.selectbox(
    "Select a funding stage",
    ["All"] + sorted(df["Funding Stage"].dropna().unique().tolist())
)

filtered_df = df.copy()

if selected_country != "All":
    filtered_df = filtered_df[filtered_df["Country"] == selected_country]

if selected_industry != "All":
    filtered_df = filtered_df[filtered_df["Industry"] == selected_industry]

if selected_stage != "All":
    filtered_df = filtered_df[filtered_df["Funding Stage"] == selected_stage]

if filtered_df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# -----------------------------
# KPI section
# -----------------------------
st.subheader("Key Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total Startups", f"{len(filtered_df):,}")
col2.metric("Average Funding ($M)", f"${filtered_df['Total Funding ($M)'].mean():,.1f}M")
col3.metric("Countries", filtered_df["Country"].nunique())
col4.metric("Total Funding ($M)", f"${filtered_df['Total Funding ($M)'].sum():,.0f}M")

# -----------------------------
# Dataset preview
# -----------------------------
st.subheader("Dataset Preview")
st.dataframe(filtered_df.head(10), use_container_width=True)

# -----------------------------
# Market analysis section
# -----------------------------
st.divider()
st.subheader("Market Analysis")

# Color palettes
industry_palette = [
    "#4F46E5", "#06B6D4", "#10B981", "#F59E0B", "#EF4444",
    "#8B5CF6", "#14B8A6", "#F97316", "#EC4899", "#3B82F6"
]

country_palette = [
    "#2563EB", "#7C3AED", "#059669", "#D97706", "#DC2626",
    "#0EA5E9", "#16A34A", "#9333EA", "#EA580C", "#E11D48"
]

stage_palette = ["#2563EB", "#7C3AED", "#F59E0B", "#10B981", "#EF4444", "#06B6D4"]

# -----------------------------
# Top industries and countries
# -----------------------------
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Top 10 Industries")
    top_industries = (
        filtered_df["Industry"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    top_industries.columns = ["Industry", "Count"]

    industries_chart = alt.Chart(top_industries).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Industry:N", sort="-y", title="Industry"),
        y=alt.Y("Count:Q", title="Number of Startups"),
        color=alt.Color("Industry:N", scale=alt.Scale(range=industry_palette), legend=None),
        tooltip=["Industry", "Count"]
    ).properties(height=350)

    st.altair_chart(industries_chart, use_container_width=True)
    st.caption("Top industries based on number of startups")

with chart_col2:
    st.subheader("Top 10 Countries")
    top_countries = (
        filtered_df["Country"]
        .value_counts()
        .head(10)
        .reset_index()
    )
    top_countries.columns = ["Country", "Count"]

    countries_chart = alt.Chart(top_countries).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Country:N", sort="-y", title="Country"),
        y=alt.Y("Count:Q", title="Number of Startups"),
        color=alt.Color("Country:N", scale=alt.Scale(range=country_palette), legend=None),
        tooltip=["Country", "Count"]
    ).properties(height=350)

    st.altair_chart(countries_chart, use_container_width=True)
    st.caption("Top countries based on number of startups")

# -----------------------------
# Funding over time
# -----------------------------
st.subheader("Total Startup Funding Over Time")

funding_by_year = (
    filtered_df
    .dropna(subset=["Founded Year", "Total Funding ($M)"])
    .groupby("Founded Year", as_index=False)["Total Funding ($M)"]
    .sum()
    .sort_values("Founded Year")
)

funding_chart = alt.Chart(funding_by_year).mark_line(point=True, strokeWidth=3, color="#2563EB").encode(
    x=alt.X("Founded Year:Q", title="Founded Year"),
    y=alt.Y("Total Funding ($M):Q", title="Total Funding ($M)"),
    tooltip=["Founded Year", "Total Funding ($M)"]
).properties(height=350)

st.altair_chart(funding_chart, use_container_width=True)

# -----------------------------
# Success score and funding stage
# -----------------------------
chart_col3, chart_col4 = st.columns(2)

with chart_col3:
    st.subheader("Average Success Score by Industry")
    success_by_industry = (
        filtered_df
        .groupby("Industry", as_index=False)["Success Score"]
        .mean()
        .sort_values("Success Score", ascending=False)
        .head(10)
    )

    success_chart = alt.Chart(success_by_industry).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Industry:N", sort="-y", title="Industry"),
        y=alt.Y("Success Score:Q", title="Average Success Score"),
        color=alt.Color("Industry:N", scale=alt.Scale(range=industry_palette), legend=None),
        tooltip=["Industry", alt.Tooltip("Success Score:Q", format=".2f")]
    ).properties(height=350)

    st.altair_chart(success_chart, use_container_width=True)

with chart_col4:
    st.subheader("Funding Stage Distribution")
    stage_distribution = (
        filtered_df["Funding Stage"]
        .value_counts()
        .reset_index()
    )
    stage_distribution.columns = ["Funding Stage", "Count"]

    stage_chart = alt.Chart(stage_distribution).mark_arc(innerRadius=70).encode(
        theta=alt.Theta("Count:Q"),
        color=alt.Color("Funding Stage:N", scale=alt.Scale(range=stage_palette)),
        tooltip=["Funding Stage", "Count"]
    ).properties(height=350)

    st.altair_chart(stage_chart, use_container_width=True)

# -----------------------------
# Valuation and revenue analysis
# -----------------------------
chart_col5, chart_col6 = st.columns(2)

with chart_col5:
    st.subheader("Average Valuation by Industry")
    valuation_by_industry = (
        filtered_df
        .dropna(subset=["Valuation ($B)"])
        .groupby("Industry", as_index=False)["Valuation ($B)"]
        .mean()
        .sort_values("Valuation ($B)", ascending=False)
        .head(10)
    )

    valuation_chart = alt.Chart(valuation_by_industry).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Industry:N", sort="-y", title="Industry"),
        y=alt.Y("Valuation ($B):Q", title="Average Valuation ($B)"),
        color=alt.Color("Industry:N", scale=alt.Scale(range=industry_palette), legend=None),
        tooltip=["Industry", alt.Tooltip("Valuation ($B):Q", format=".2f")]
    ).properties(height=350)

    st.altair_chart(valuation_chart, use_container_width=True)

with chart_col6:
    st.subheader("Average Annual Revenue by Country")
    revenue_by_country = (
        filtered_df
        .dropna(subset=["Annual Revenue ($M)"])
        .groupby("Country", as_index=False)["Annual Revenue ($M)"]
        .mean()
        .sort_values("Annual Revenue ($M)", ascending=False)
        .head(10)
    )

    revenue_chart = alt.Chart(revenue_by_country).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Country:N", sort="-y", title="Country"),
        y=alt.Y("Annual Revenue ($M):Q", title="Average Annual Revenue ($M)"),
        color=alt.Color("Country:N", scale=alt.Scale(range=country_palette), legend=None),
        tooltip=["Country", alt.Tooltip("Annual Revenue ($M):Q", format=".2f")]
    ).properties(height=350)

    st.altair_chart(revenue_chart, use_container_width=True)

# -----------------------------
# Scatter plot
# -----------------------------
st.subheader("Funding vs Success Score")

scatter_data = filtered_df.dropna(subset=["Total Funding ($M)", "Success Score", "Industry"])

scatter_chart = alt.Chart(scatter_data).mark_circle(size=90, opacity=0.7).encode(
    x=alt.X("Total Funding ($M):Q", title="Total Funding ($M)"),
    y=alt.Y("Success Score:Q", title="Success Score"),
    color=alt.Color("Industry:N", scale=alt.Scale(range=industry_palette)),
    tooltip=[
        "Startup Name",
        "Country",
        "Industry",
        "Funding Stage",
        alt.Tooltip("Total Funding ($M):Q", format=".2f"),
        alt.Tooltip("Success Score:Q", format=".2f")
    ]
).properties(height=400)

st.altair_chart(scatter_chart, use_container_width=True)

# -----------------------------
# Additional Charts
# -----------------------------
st.divider()

st.subheader("Employees vs Annual Revenue")

employee_revenue_data = filtered_df.dropna(
    subset=["Number of Employees", "Annual Revenue ($M)"]
)

# LIMIT data → VERY IMPORTANT (prevents overcrowding)
employee_revenue_data = employee_revenue_data.sample(
    n=min(800, len(employee_revenue_data)),
    random_state=1
)

chart = alt.Chart(employee_revenue_data).mark_circle(
    size=70,
    opacity=0.4
).encode(
    x=alt.X(
        "Number of Employees:Q",
        title="Number of Employees",
        scale=alt.Scale(domain=[0, 5000])  # FIX AXIS
    ),
    y=alt.Y(
        "Annual Revenue ($M):Q",
        title="Annual Revenue ($M)",
        scale=alt.Scale(domain=[0, 1000])  # FIX AXIS
    ),
    color=alt.Color("Industry:N"),
    tooltip=[
    "Startup Name",
    "Country",
    "Industry",
    alt.Tooltip("Number of Employees:Q", title="Employees"),
    alt.Tooltip("Annual Revenue ($M):Q", title="Revenue ($M)", format=".2f")
]
).properties(
    height=400
).interactive()

st.altair_chart(chart, use_container_width=True)   

# -----------------------------
# Dynamic insight
# -----------------------------
top_industry = filtered_df["Industry"].value_counts().idxmax()
top_country = filtered_df["Country"].value_counts().idxmax()

st.info(
    f"Insight: The most active industry is **{top_industry}**, while **{top_country}** leads in number of startups. "
    "Funding trends show how investment activity evolves over time, and valuation / success metrics help compare market performance across sectors."
)

# -----------------------------
# Top funded startups table
# -----------------------------
st.subheader("Top 10 Funded Startups")
top_funded = filtered_df.sort_values(
    by="Total Funding ($M)",
    ascending=False
)[["Startup Name", "Country", "Industry", "Funding Stage", "Total Funding ($M)"]].head(10)

st.dataframe(top_funded.sort_values(by="Total Funding ($M)", ascending=False), use_container_width=True)