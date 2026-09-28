# F1 Winners (1950–2025) — Data Analytics Project

## Video link:
https://youtu.be/AQWHPgqI3xw?si=83u_fvUHYucY1qmY

## Overview
This project is a data analytics project built around a CSV dataset of Formula 1 race winners from 1950 to 2025.  
The goal is to load the dataset, do simple cleaning, and generate clear summaries + visualizations that show who dominates (drivers/teams) and how races are distributed over time and across continents.

## Dataset
File: `data/winners_f1_1950_2025_v2.csv`  
Main fields used in the analysis include:
- Date
- Year
- Continent
- Grand Prix
- Circuit
- Winner (driver)
- Team
- Laps
- Time (race time)

## Features
- Loads and validates the CSV dataset from the `data/` folder
- Generates aggregated analytics:
  - Top drivers by total wins
  - Top teams by total wins
  - Races per year (trend)
  - Races per decade
  - Races by continent
- Exports results as both **CSV tables** and **PNG charts** into `results/`

## Key Insights (from this dataset)
- A small set of drivers and teams account for a large share of wins
- The number of races per season changes noticeably across decades
- Race locations are unevenly distributed by continent (some continents host significantly more races)

## Outputs
After running the script, the project creates a `results/` folder containing:
- `summary.txt`
- `top_drivers.csv`, `top_teams.csv`
- `wins_by_year.csv`, `wins_by_decade.csv`, `wins_by_continent.csv`
- Charts:
  - `top_drivers.png`
  - `top_teams.png`
  - `wins_by_year.png`
  - `wins_by_decade.png`
  - `wins_by_continent.png`

## Tools & Technologies
- Python
- Pandas
- Matplotlib
- Git/GitHub (terminal workflow)

## How to Run
From inside your project folder:

```bash
pip install -r requirements.txt
python main.py

