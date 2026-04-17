# Smart Holiday Delivery Scheduler

## Author

Danielius Žarkich

## Description

This project is a small automation tool that helps avoid **dead-on-arrival** style shipping problems caused by **public holiday closures** along a route. You enter an **origin** country, a **destination** country, and a **planned ship date**. The scheduler checks public holidays in the **origin**, any **transit hubs** in the model, and the **destination** for each day of a configurable corridor window. If a holiday falls on a day when the shipment is treated as being in that country, the run is **flagged** and the tool suggests an **earliest safe ship date** with no conflicts in that model.

Example: shipping from **Lithuania** to **Germany** with **Poland** as a transit hub. If the corridor window includes a Polish public holiday while the shipment is “in Poland,” that date is reported so teams can reschedule before storage or handling fees pile up.

Public holidays come from the **[python-holidays](https://github.com/vacanza/python-holidays)** library (country calendars, not carrier-specific rules).

## Requirements

- Python 3.10+ recommended  
- Dependencies listed in `requirements.txt` (`holidays`, `streamlit`)

## Installation

From this project folder:

```bash
python -m pip install -r requirements.txt
```

## How to Run

### Command-line interface (`delivery_scheduler.py`)

List configured corridors:

```bash
python delivery_scheduler.py --list-routes
```

Check a specific ship date (ISO date `YYYY-MM-DD`):

```bash
python delivery_scheduler.py --origin LT --destination DE --date 2026-11-09
```

Short flags:

```bash
python delivery_scheduler.py -o LT -d DE -t 2026-06-10
```

Machine-readable JSON (for scripts or integrations):

```bash
python delivery_scheduler.py -o LT -d DE -t 2026-06-10 --json
```

### Streamlit app

```bash
python -m streamlit run streamlit_app.py
```

Then choose a corridor and a ship date in the browser.

### Holiday world comparison (`holiday_world_comparison.ipynb`)

Install dependencies (includes `nbformat` and `ipython` for Plotly inside notebooks), then either open the notebook in VS Code / Cursor or run:

```bash
python -m jupyter notebook holiday_world_comparison.ipynb
```

If `jupyter` is not found, use `python -m jupyter` (the `Scripts` folder may not be on your PATH on Windows).

**Plotly in notebooks:** If charts fail with errors about `nbformat` or `ipython`, run `python -m pip install -r requirements.txt` again. The notebook also falls back to opening figures in your **web browser** when inline rendering is not available.

### Story charts (`logistics_story_charts.ipynb` + `holiday_viz.py`)

- **Route health map (Folium):** corridor line segments colored by holiday risk per leg; city pop-ups reference conflicts from the scheduler.
- **Holiday Gantt (Plotly):** naive vs “smart” truck timelines with gray holiday bands.
- **Friction heatmap (Seaborn):** year calendar heatmap of a simple multi-country friction score.

Open `logistics_story_charts.ipynb` after installing dependencies.

## Features

- **Route-aware checks**: Each route defines **legs** as day offsets from the ship date, so only the relevant country is checked on each day (origin, transit, destination).
- **Conflict report**: Shows each conflicting calendar day, corridor day offset, country code, and holiday name when possible.
- **Safe date suggestion**: Searches forward from the proposed ship date for the first day with no holiday conflicts along the modeled window (bounded horizon; see code for `max_ahead_days`).
- **CLI and Streamlit**: Same core logic from `delivery_scheduler.py` in a terminal workflow or a simple web UI.

## Configuring routes

Corridors and **leg** timings live in the `ROUTES` dictionary in `delivery_scheduler.py`. Each leg is `(country_code, start_offset, end_offset)` with half-open intervals `[start, end)` relative to day `0` (ship date). **Transit hub** labels are informational; the important part is which **country code** applies on which **offsets**. Adjust legs to match your carrier’s typical lead times and paths.

## Limitations

- Leg lengths are **placeholders**, not live carrier data.  
- **Weekends** are not modeled separately from holidays (only public holidays from `python-holidays`).  
- **Customs, strikes, weather, and warehouse hours** are out of scope unless you extend the code.
