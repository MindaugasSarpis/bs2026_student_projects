from pathlib import Path

import pandas as pd
import plotly.express as px
from flask import Flask, render_template_string, request

app = Flask(__name__)


def load_data():
    project_root = Path(__file__).resolve().parent
    data_path = project_root / "data" / "winners_f1_1950_2025_v2.csv"

    df = pd.read_csv(data_path)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    df["decade"] = (df["year"] // 10) * 10

    return df


TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>F1 Dashboard | Agshin Osmanov</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <style>
        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            font-family: Arial, Helvetica, sans-serif;
            background: #0f1115;
            color: #f4f4f4;
        }

        .container {
            width: min(1200px, 92%);
            margin: 0 auto;
        }

        .hero {
            padding: 40px 0 20px;
        }

        .hero h1 {
            margin: 0 0 10px;
            font-size: 2.4rem;
        }

        .hero p {
            margin: 0;
            color: #b7bec7;
        }

        .filter-bar {
            margin: 24px 0;
            padding: 18px;
            background: #171a21;
            border-radius: 16px;
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: end;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        label {
            font-size: 0.95rem;
            color: #c9d1d9;
        }

        select, button {
            padding: 10px 12px;
            border-radius: 10px;
            border: none;
            font-size: 0.95rem;
        }

        button {
            cursor: pointer;
            background: #e10600;
            color: white;
            font-weight: bold;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin: 20px 0 28px;
        }

        .card {
            background: #171a21;
            border-radius: 18px;
            padding: 20px;
        }

        .card h3 {
            margin: 0 0 8px;
            font-size: 0.95rem;
            color: #b7bec7;
            font-weight: normal;
        }

        .card p {
            margin: 0;
            font-size: 1.8rem;
            font-weight: bold;
        }

        .chart-card {
            background: #171a21;
            border-radius: 18px;
            padding: 20px;
            margin-bottom: 20px;
        }

        .chart-card h2 {
            margin-top: 0;
            margin-bottom: 14px;
            font-size: 1.2rem;
        }

        .footer {
            padding: 20px 0 40px;
            color: #9aa4af;
            text-align: center;
        }

        .table-wrap {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            color: white;
        }

        th, td {
            padding: 10px;
            border-bottom: 1px solid #2a2f3a;
            text-align: left;
        }

        th {
            color: #b7bec7;
            font-weight: normal;
        }
    </style>
</head>
<body>
    <div class="container">
        <section class="hero">
            <h1>Formula 1 Winners Dashboard</h1>
            <p>
                Interactive dashboard based on historical Formula 1 winners data from 1950 to 2025.
            </p>
        </section>

        <form method="GET" class="filter-bar">
            <div class="filter-group">
                <label for="continent">Continent</label>
                <select name="continent" id="continent">
                    {% for c in continents %}
                        <option value="{{ c }}" {% if c == selected_continent %}selected{% endif %}>{{ c }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="filter-group">
                <label for="start_year">Start year</label>
                <select name="start_year" id="start_year">
                    {% for y in years %}
                        <option value="{{ y }}" {% if y == selected_start_year %}selected{% endif %}>{{ y }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="filter-group">
                <label for="end_year">End year</label>
                <select name="end_year" id="end_year">
                    {% for y in years %}
                        <option value="{{ y }}" {% if y == selected_end_year %}selected{% endif %}>{{ y }}</option>
                    {% endfor %}
                </select>
            </div>

            <button type="submit">Apply filters</button>
        </form>

        <section class="cards">
            <div class="card">
                <h3>Total races</h3>
                <p>{{ total_races }}</p>
            </div>
            <div class="card">
                <h3>Unique winners</h3>
                <p>{{ unique_winners }}</p>
            </div>
            <div class="card">
                <h3>Unique teams</h3>
                <p>{{ unique_teams }}</p>
            </div>
            <div class="card">
                <h3>Top winner</h3>
                <p style="font-size: 1.1rem;">{{ top_winner }}</p>
            </div>
        </section>

        <section class="chart-card">
            <h2>Top 10 Drivers by Wins</h2>
            {{ chart_top_drivers|safe }}
        </section>

        <section class="chart-card">
            <h2>Top 10 Teams by Wins</h2>
            {{ chart_top_teams|safe }}
        </section>

        <section class="chart-card">
            <h2>Races by Year</h2>
            {{ chart_year|safe }}
        </section>

        <section class="chart-card">
            <h2>Races by Decade</h2>
            {{ chart_decade|safe }}
        </section>

        <section class="chart-card">
            <h2>Races by Continent</h2>
            {{ chart_continent|safe }}
        </section>

        <section class="chart-card">
            <h2>Top 10 Drivers Table</h2>
            <div class="table-wrap">
                {{ drivers_table|safe }}
            </div>
        </section>

        <div class="footer">
            Created by Agshin Osmanov
        </div>
    </div>
</body>
</html>
"""


@app.route("/")
def dashboard():
    df = load_data()

    all_years = sorted(df["year"].dropna().astype(int).unique().tolist())
    continents = ["All"] + sorted(df["continent"].dropna().unique().tolist())

    selected_continent = request.args.get("continent", "All")
    selected_start_year = int(request.args.get("start_year", all_years[0]))
    selected_end_year = int(request.args.get("end_year", all_years[-1]))

    filtered_df = df[(df["year"] >= selected_start_year) & (df["year"] <= selected_end_year)]

    if selected_continent != "All":
        filtered_df = filtered_df[filtered_df["continent"] == selected_continent]

    total_races = len(filtered_df)
    unique_winners = filtered_df["winner_name"].nunique()
    unique_teams = filtered_df["team"].nunique()

    wins_by_driver = filtered_df["winner_name"].value_counts().head(10)
    wins_by_team = filtered_df["team"].value_counts().head(10)
    wins_by_year = filtered_df.groupby("year").size().reset_index(name="wins")
    wins_by_decade = filtered_df.groupby("decade").size().reset_index(name="wins")
    wins_by_continent = filtered_df["continent"].value_counts().reset_index()
    wins_by_continent.columns = ["continent", "wins"]

    if not wins_by_driver.empty:
        top_winner = f"{wins_by_driver.index[0]} ({wins_by_driver.iloc[0]} wins)"
    else:
        top_winner = "No data"

    fig_top_drivers = px.bar(
        wins_by_driver.sort_values(),
        orientation="h",
        labels={"value": "Wins", "index": "Driver"},
    )
    fig_top_drivers.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        height=450,
    )

    fig_top_teams = px.bar(
        wins_by_team.sort_values(),
        orientation="h",
        labels={"value": "Wins", "index": "Team"},
    )
    fig_top_teams.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        height=450,
    )

    fig_year = px.line(
        wins_by_year,
        x="year",
        y="wins",
        markers=True,
        labels={"year": "Year", "wins": "Races"},
    )
    fig_year.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        height=420,
    )

    fig_decade = px.bar(
        wins_by_decade,
        x="decade",
        y="wins",
        labels={"decade": "Decade", "wins": "Races"},
    )
    fig_decade.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        height=420,
    )

    fig_continent = px.bar(
        wins_by_continent.sort_values("wins"),
        x="wins",
        y="continent",
        orientation="h",
        labels={"wins": "Races", "continent": "Continent"},
    )
    fig_continent.update_layout(
        template="plotly_dark",
        margin=dict(l=20, r=20, t=20, b=20),
        height=420,
    )

    drivers_table_df = wins_by_driver.reset_index()
    drivers_table_df.columns = ["Driver", "Wins"]
    drivers_table = drivers_table_df.to_html(index=False, classes="data-table")

    return render_template_string(
        TEMPLATE,
        total_races=total_races,
        unique_winners=unique_winners,
        unique_teams=unique_teams,
        top_winner=top_winner,
        chart_top_drivers=fig_top_drivers.to_html(full_html=False, include_plotlyjs=False),
        chart_top_teams=fig_top_teams.to_html(full_html=False, include_plotlyjs=False),
        chart_year=fig_year.to_html(full_html=False, include_plotlyjs=False),
        chart_decade=fig_decade.to_html(full_html=False, include_plotlyjs=False),
        chart_continent=fig_continent.to_html(full_html=False, include_plotlyjs=False),
        drivers_table=drivers_table,
        continents=continents,
        years=all_years,
        selected_continent=selected_continent,
        selected_start_year=selected_start_year,
        selected_end_year=selected_end_year,
    )


if __name__ == "__main__":
    app.run(debug=True)