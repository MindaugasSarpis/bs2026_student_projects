# Order Arrival Calculator

## Author

Danielius Žarkich

## Description

A small **Streamlit** app for sales and logistics: pick a **product** (supplier + port of loading), a **destination (POD)**, and a **planned contract sign date**. The tool shows **transit time (TT)**, **POD offset**, **recommended lead time**, and **shipping / delivery ETAs**. It flags **weekend** delivery dates and **public holidays** in the POD country on the delivery ETA (via **python-holidays**).

A second tab, **Lane insights**, shows a **world map** and **TT comparison chart** for all origins in `data/TT_Offset.csv` toward the selected POD.

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

- `data/Products_Suppliers.csv` — articles, suppliers, **POL** (origin country)  
- `data/TT_Offset.csv` — **TT** and **POD offset** by **POL → POD** pair  

Extend `lane_insights.POL_COUNTRY_TO_ISO3` if you add new POL country labels so the map can resolve ISO codes.

## Limitations

- ETAs use **calendar-day** arithmetic (not business days).  
- Holiday checks use **national public holidays** for the POD country, not carrier-specific rules.
