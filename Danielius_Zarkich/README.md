# Order Arrival Calculator

## Author

Danielius Žarkich

## Description

The app has two tabs:

1. **Order calculator** - Pick a product (article, description, supplier, POL in the dropdown), a destination (POD), and a planned contract sign date. You get transit time (TT), POD offset, recommended lead time, shipping ETA and delivery ETA. The app warns if the delivery ETA is a weekend or a public holiday in the POD country (python-holidays).
2. **Lane insights** - Choose a POD and see a world map (TT by origin country) and a horizontal TT comparison chart for all POL rows in `data/TT_Offset.csv` for that POD.

## Requirements

- Python 3.10+ recommended  
- Dependencies: see `requirements.txt` (`streamlit`, `pandas`, `plotly`, `holidays`)

## Installation

From this project folder:

```bash
python -m pip install -r requirements.txt
```

## How to run

```bash
python -m streamlit run streamlit_app.py
```

## Data

- `data/Products_Suppliers.csv` - articles, suppliers, **POL** (origin country)  
- `data/TT_Offset.csv` - **TT** and **POD offset** by **POL → POD** pair

If you add data:

- New **POL** labels in the CSV → extend `lane_insights.POL_COUNTRY_TO_ISO3` (map).
- New **POD** labels → extend `holiday_checks.POD_COUNTRY_TO_ISO2` (delivery holiday check) and `lane_insights.POD_LATLON` (map marker).

