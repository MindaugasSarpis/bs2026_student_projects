import argparse
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401
import plotly.express as px
import plotly.offline as pyo


# ---- PDF FONT SETTINGS ----
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 12

# ---- HARD CODED THRESHOLDS ----
THRESHOLDS = {
    "Temperature": {"low": None, "high": 30.0},
    "CO2PPM": {"low": None, "high": 1000.0},
    "PressureHpa": {"low": 980.0, "high": 1035.0},
    "HumidityPct": {"low": 30.0, "high": 70.0},
}


def analyze_thresholds(df, numeric_columns):
    summary = []

    for col in numeric_columns:
        low = THRESHOLDS[col]["low"]
        high = THRESHOLDS[col]["high"]

        low_count = len(df[df[col] < low]) if low is not None else 0
        high_count = len(df[df[col] > high]) if high is not None else 0

        summary.append({
            "Metric": col,
            "LowThreshold": low,
            "LowBreaches": low_count,
            "HighThreshold": high,
            "HighBreaches": high_count,
            "TotalAlerts": low_count + high_count,
        })

    return pd.DataFrame(summary)


def normalize_series(series):
    min_val = series.min()
    max_val = series.max()

    if pd.isna(min_val) or pd.isna(max_val):
        return pd.Series([0.0] * len(series), index=series.index)

    if max_val == min_val:
        return pd.Series([50.0] * len(series), index=series.index)

    return ((series - min_val) / (max_val - min_val)) * 100.0


def add_cover_tables_page(pdf, df, summary_df, alert_summary_df):
    fig, ax = plt.subplots(figsize=(11.69, 8.27))  # A4 landscape
    ax.axis("off")

    start_time = df["Created"].min()
    end_time = df["Created"].max()

    fig.text(0.5, 0.96, "Air Quality Report Summary", ha="center", va="top", fontsize=16, fontweight="bold")

    info_text = (
        f"Records: {len(df)}\n"
        f"From: {start_time}\n"
        f"To: {end_time}"
    )
    fig.text(0.05, 0.90, info_text, ha="left", va="top", fontsize=12)

    fig.text(0.05, 0.80, "Sensor Statistics", ha="left", va="top", fontsize=13, fontweight="bold")
    table1 = ax.table(
        cellText=summary_df.round(2).fillna("").values,
        colLabels=summary_df.columns,
        cellLoc="center",
        bbox=[0.05, 0.47, 0.90, 0.25],
    )
    table1.auto_set_font_size(False)
    table1.set_fontsize(11)
    table1.scale(1, 1.3)

    fig.text(0.05, 0.40, "Threshold Summary", ha="left", va="top", fontsize=13, fontweight="bold")
    table2 = ax.table(
        cellText=alert_summary_df.fillna("").values,
        colLabels=alert_summary_df.columns,
        cellLoc="center",
        bbox=[0.05, 0.08, 0.90, 0.25],
    )
    table2.auto_set_font_size(False)
    table2.set_fontsize(10)
    table2.scale(1, 1.3)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_clean_multiline_timeseries(pdf, df):
    cols = ["Temperature", "CO2PPM", "HumidityPct"]
    cols = [c for c in cols if c in df.columns]

    if len(cols) < 2:
        return

    fig, ax = plt.subplots(figsize=(11, 6))

    color_map = {
        "Temperature": "red",
        "CO2PPM": "blue",
        "HumidityPct": "green",
    }

    label_map = {
        "Temperature": "Temperature",
        "CO2PPM": "CO2 (Air Quality)",
        "HumidityPct": "Humidity",
    }

    for col in cols:
        ax.plot(
            df["Created"],
            normalize_series(df[col]),
            label=label_map[col],
            color=color_map[col],
            linewidth=2,
        )

    ax.set_title("Normalized Multi-line Time Series")
    ax.set_xlabel("Time")
    ax.set_ylabel("Normalized Value (%)")
    ax.set_ylim(0, 100)
    ax.grid(True, alpha=0.3)
    ax.legend()
    fig.autofmt_xdate()

    note = (
        "Temperature, CO2, and Humidity are normalized to 0-100 "
        "so they can be compared on the same chart."
    )
    fig.text(0.01, 0.01, note, fontsize=10)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_stacked_area_chart(pdf, df):
    cols = ["Temperature", "CO2PPM", "HumidityPct"]
    cols = [c for c in cols if c in df.columns]

    if len(cols) < 2:
        return

    data = [normalize_series(df[col]).values for col in cols]
    labels = {
        "Temperature": "Temperature",
        "CO2PPM": "CO2 (Air Quality)",
        "HumidityPct": "Humidity",
    }
    colors = {
        "Temperature": "red",
        "CO2PPM": "blue",
        "HumidityPct": "green",
    }

    fig, ax = plt.subplots(figsize=(11, 6))
    ax.stackplot(
        df["Created"],
        data,
        labels=[labels[col] for col in cols],
        colors=[colors[col] for col in cols],
        alpha=0.7,
    )

    ax.set_title("Stacked Area Chart (Normalized)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Normalized Contribution")
    ax.legend(loc="upper left")
    ax.grid(True, alpha=0.3)
    fig.autofmt_xdate()

    note = "Values are normalized before stacking. This chart is for visual comparison."
    fig.text(0.01, 0.01, note, fontsize=10)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_airquality_heatmap(pdf, df):
    if "CO2PPM" not in df.columns:
        return

    heatmap_df = df[["Created", "CO2PPM"]].copy()

    start = heatmap_df["Created"].min()
    heatmap_df["HourIndex"] = (
        (heatmap_df["Created"] - start).dt.total_seconds() / 3600
    ).astype(int)

    hourly = heatmap_df.groupby("HourIndex")["CO2PPM"].mean()

    if hourly.empty:
        return

    data = np.array([hourly.values])

    fig, ax = plt.subplots(figsize=(12, 3))
    im = ax.imshow(data, aspect="auto", cmap="viridis", interpolation="nearest")

    ax.set_title("Air Quality (CO2) Heatmap - Hourly")
    ax.set_xlabel("Hours Since Start")
    ax.set_yticks([])

    total_hours = len(hourly)
    step = max(1, total_hours // 10)
    ticks = list(range(0, total_hours, step))
    if ticks and ticks[-1] != total_hours - 1:
        ticks.append(total_hours - 1)
    elif not ticks:
        ticks = [0]

    ax.set_xticks(ticks)
    ax.set_xticklabels([str(t) for t in ticks])

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("CO2 (PPM)")

    note = "Each column represents the average CO2 value for one hour since the first reading."
    fig.text(0.01, 0.01, note, fontsize=10)

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def add_threshold_zones(ax, low, high):
    ymin, ymax = ax.get_ylim()

    if low is not None and high is not None:
        ax.axhspan(ymin, low, alpha=0.12, color="red")
        ax.axhspan(low, high, alpha=0.12, color="green")
        ax.axhspan(high, ymax, alpha=0.12, color="red")
    elif low is not None:
        ax.axhspan(ymin, low, alpha=0.12, color="red")
        ax.axhspan(low, ymax, alpha=0.12, color="green")
    elif high is not None:
        ax.axhspan(ymin, high, alpha=0.12, color="green")
        ax.axhspan(high, ymax, alpha=0.12, color="red")


def add_3d_scatter_pdf(pdf, df):
    required = ["Temperature", "HumidityPct", "CO2PPM"]
    if not all(col in df.columns for col in required):
        return

    plot_df = df[required + ["Created"]].copy()

    max_points = 3000
    if len(plot_df) > max_points:
        plot_df = plot_df.iloc[::max(1, len(plot_df) // max_points)].copy()

    plot_df["TimeHours"] = (
        (plot_df["Created"] - plot_df["Created"].min()).dt.total_seconds() / 3600.0
    )

    fig = plt.figure(figsize=(11, 8))
    ax = fig.add_subplot(111, projection="3d")

    scatter = ax.scatter(
        plot_df["Temperature"],
        plot_df["HumidityPct"],
        plot_df["CO2PPM"],
        c=plot_df["TimeHours"],
        cmap="viridis",
        s=18,
        alpha=0.8,
    )

    ax.set_title("3D Scatter: Temperature vs Humidity vs CO2")
    ax.set_xlabel("Temperature")
    ax.set_ylabel("Humidity (%)")
    ax.set_zlabel("CO2 (PPM)")

    cbar = fig.colorbar(scatter, ax=ax, pad=0.1)
    cbar.set_label("Hours Since Start")

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def generate_html_dashboard(df, output_html):
    sections = []

    if all(col in df.columns for col in ["Temperature", "CO2PPM", "HumidityPct"]):
        fig_multi = px.line(
            df,
            x="Created",
            y=["Temperature", "CO2PPM", "HumidityPct"],
            title="Temperature, CO2, and Humidity Over Time",
        )
        sections.append(pyo.plot(fig_multi, include_plotlyjs="cdn", output_type="div"))

    if "CO2PPM" in df.columns:
        heatmap_df = df[["Created", "CO2PPM"]].copy()
        start = heatmap_df["Created"].min()
        heatmap_df["HourIndex"] = (
            (heatmap_df["Created"] - start).dt.total_seconds() / 3600
        ).astype(int)
        hourly = heatmap_df.groupby("HourIndex")["CO2PPM"].mean().reset_index()

        if not hourly.empty:
            heat_data = np.array([hourly["CO2PPM"].values])
            fig_heat = px.imshow(
                heat_data,
                aspect="auto",
                labels={"x": "Hours Since Start", "color": "CO2 (PPM)"},
                title="Air Quality Heatmap - Hourly",
            )
            fig_heat.update_yaxes(showticklabels=False)
            sections.append(pyo.plot(fig_heat, include_plotlyjs=False, output_type="div"))

    if all(col in df.columns for col in ["Temperature", "HumidityPct", "CO2PPM"]):
        plot_df = df[["Created", "Temperature", "HumidityPct", "CO2PPM"]].copy()
        plot_df["HoursSinceStart"] = (
            (plot_df["Created"] - plot_df["Created"].min()).dt.total_seconds() / 3600.0
        )

        max_points = 5000
        if len(plot_df) > max_points:
            plot_df = plot_df.iloc[::max(1, len(plot_df) // max_points)].copy()

        fig_3d = px.scatter_3d(
            plot_df,
            x="Temperature",
            y="HumidityPct",
            z="CO2PPM",
            color="HoursSinceStart",
            title="3D Scatter: Temperature vs Humidity vs CO2",
            labels={
                "Temperature": "Temperature",
                "HumidityPct": "Humidity (%)",
                "CO2PPM": "CO2 (PPM)",
                "HoursSinceStart": "Hours Since Start",
            },
        )
        sections.append(pyo.plot(fig_3d, include_plotlyjs=False, output_type="div"))

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Air Quality Dashboard</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f8f9fb;
        }}
        h1 {{
            margin-bottom: 10px;
        }}
        .chart {{
            background: white;
            padding: 16px;
            margin-bottom: 24px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
    </style>
</head>
<body>
    <h1>Air Quality Dashboard</h1>
    <p>Generated from sensor data.</p>
    {''.join(f'<div class="chart">{section}</div>' for section in sections)}
</body>
</html>
"""

    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)


def analyze_air_quality(csv_file, output_base):
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        sys.exit(1)

    output_pdf = f"{output_base}.pdf"
    output_html = f"{output_base}.html"

    df = pd.read_csv(csv_file)

    if "Created" not in df.columns:
        raise ValueError("CSV must contain 'Created' column.")

    df["Created"] = pd.to_datetime(df["Created"], errors="coerce")
    df = df.dropna(subset=["Created"]).sort_values("Created")

    numeric_columns = ["Temperature", "CO2PPM", "PressureHpa", "HumidityPct"]
    numeric_columns = [c for c in numeric_columns if c in df.columns]

    if not numeric_columns:
        raise ValueError("No valid numeric columns found.")

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=numeric_columns)

    if df.empty:
        raise ValueError("No valid rows remain after cleaning the data.")

    summary_df = pd.DataFrame([
        {
            "Metric": col,
            "Min": df[col].min(),
            "Max": df[col].max(),
            "Avg": df[col].mean(),
        }
        for col in numeric_columns
    ])

    alert_summary_df = analyze_thresholds(df, numeric_columns)

    with PdfPages(output_pdf) as pdf:
        add_cover_tables_page(pdf, df, summary_df, alert_summary_df)
        add_clean_multiline_timeseries(pdf, df)
        add_stacked_area_chart(pdf, df)
        add_airquality_heatmap(pdf, df)
        add_3d_scatter_pdf(pdf, df)

        for col in numeric_columns:
            fig, ax = plt.subplots(figsize=(11, 6))

            ax.plot(df["Created"], df[col], label=col, linewidth=1.8)
            ax.set_title(f"{col} Over Time")
            ax.set_xlabel("Time")
            ax.set_ylabel(col)
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate()

            low = THRESHOLDS[col]["low"]
            high = THRESHOLDS[col]["high"]

            y_min = df[col].min()
            y_max = df[col].max()
            padding = (y_max - y_min) * 0.1 if y_max != y_min else 1
            ax.set_ylim(y_min - padding, y_max + padding)

            add_threshold_zones(ax, low, high)

            min_idx = df[col].idxmin()
            max_idx = df[col].idxmax()

            ax.scatter(df.loc[min_idx, "Created"], df.loc[min_idx, col], label="Min", zorder=5)
            ax.scatter(df.loc[max_idx, "Created"], df.loc[max_idx, col], label="Max", zorder=5)

            if low is not None:
                low_points = df[df[col] < low]
                ax.axhline(low, linestyle="--", label=f"Low ({low})")
                if not low_points.empty:
                    ax.scatter(low_points["Created"], low_points[col], label="Low alerts", zorder=5)

            if high is not None:
                high_points = df[df[col] > high]
                ax.axhline(high, linestyle="--", label=f"High ({high})")
                if not high_points.empty:
                    ax.scatter(high_points["Created"], high_points[col], label="High alerts", zorder=5)

            ax.legend()
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)

    generate_html_dashboard(df, output_html)

    print(f"PDF saved: {output_pdf}")
    print(f"HTML saved: {output_html}")


def main():
    parser = argparse.ArgumentParser(description="Air quality CSV analyzer")
    parser.add_argument("input_csv", help="Path to input CSV file")
    parser.add_argument("output_name", help="Output base name without extension")

    args = parser.parse_args()
    analyze_air_quality(args.input_csv, args.output_name)

# -- RUN AUTOMATICALLY
if __name__ == "__main__":
    main()