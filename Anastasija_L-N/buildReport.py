import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


# ---- PDF FONT SETTINGS ----
plt.rcParams["font.family"] = "Times New Roman"
plt.rcParams["font.size"] = 12

CONFIG_FILENAME = "config.json"
OUTPUT_DIRNAME = "output"


def load_thresholds(config_path):
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r", encoding="utf-8") as config_file:
        config = json.load(config_file)

    thresholds = config.get("thresholds", config)
    if not isinstance(thresholds, dict):
        raise ValueError("Config file must contain a thresholds object.")

    normalized_thresholds = {}
    for metric, values in thresholds.items():
        if not isinstance(values, dict):
            raise ValueError(f"Threshold config for '{metric}' must be an object.")

        low = values.get("low")
        high = values.get("high")

        if low is not None and not isinstance(low, (int, float)):
            raise ValueError(f"Low threshold for '{metric}' must be a number or null.")

        if high is not None and not isinstance(high, (int, float)):
            raise ValueError(f"High threshold for '{metric}' must be a number or null.")

        normalized_thresholds[metric] = {
            "low": float(low) if low is not None else None,
            "high": float(high) if high is not None else None,
        }

    return normalized_thresholds


def get_thresholds_for_metric(thresholds, metric):
    metric_thresholds = thresholds.get(metric, {})
    return {
        "low": metric_thresholds.get("low"),
        "high": metric_thresholds.get("high"),
    }


def analyze_thresholds(df, numeric_columns, thresholds):
    summary = []

    for col in numeric_columns:
        metric_thresholds = get_thresholds_for_metric(thresholds, col)
        low = metric_thresholds["low"]
        high = metric_thresholds["high"]

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



def analyze_air_quality(csv_file, output_file_name, config_path=None):
    if not os.path.exists(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))

    if config_path is None:
        config_path = os.path.join(script_dir, CONFIG_FILENAME)

    thresholds = load_thresholds(config_path)

    output_dir = os.path.join(script_dir, OUTPUT_DIRNAME)
    os.makedirs(output_dir, exist_ok=True)

    output_pdf = os.path.join(output_dir, f"{output_file_name}.pdf")

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

    alert_summary_df = analyze_thresholds(df, numeric_columns, thresholds)

    with PdfPages(output_pdf) as pdf:
        add_cover_tables_page(pdf, df, summary_df, alert_summary_df)
  

        for col in numeric_columns:
            fig, ax = plt.subplots(figsize=(11, 6))

            ax.plot(df["Created"], df[col], label=col, linewidth=1.8)
            ax.set_title(f"{col} Over Time")
            ax.set_xlabel("Time")
            ax.set_ylabel(col)
            ax.grid(True, alpha=0.3)
            fig.autofmt_xdate()

            metric_thresholds = get_thresholds_for_metric(thresholds, col)
            low = metric_thresholds["low"]
            high = metric_thresholds["high"]

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
            
        add_clean_multiline_timeseries(pdf, df)
        add_stacked_area_chart(pdf, df)
    print(f"PDF saved: {output_pdf}")


def main():
    parser = argparse.ArgumentParser(description="Air quality CSV analyzer")
    parser.add_argument("input_csv", help="Path to input CSV file")
    parser.add_argument("output_file_name", help="Output file name without extension")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to threshold config JSON file. Defaults to config.json next to this script.",
    )

    args = parser.parse_args()
    analyze_air_quality(args.input_csv, args.output_file_name, args.config)

# -- RUN AUTOMATICALLY
if __name__ == "__main__":
    main()
