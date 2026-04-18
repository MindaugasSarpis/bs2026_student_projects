# Air Quality Analyzer & Report Generator

## Description
A data analysis and visualization tool for air quality sensor data (Temperature, PPT, Humidity, Pressure).

This project processes CSV sensor logs and generates:
- A PDF report with statistics and charts  

It is designed to transform raw sensor data into insights and presentation-ready outputs.

---

## Features
- Automatic Data Analysis
  - Cleans and processes CSV sensor data
  - Computes min, max, and average statistics

- Threshold Monitoring
  - Detects values outside safe ranges
  - Generates alert summaries

- PDF Report Generation
  - Summary tables
  - Time series charts
  - Stacked area charts
  - Heatmaps (CO₂ over time)
  - 3D scatter visualizations

- Advanced Visualizations
  - Normalized multi-metric comparison
  - Threshold zone highlighting
  - Time-based 3D data exploration

---

## Installation

### 1. Clone the repository
https://github.com/analicm/bs2026_student_projects.git

### 2. Make sure Python is installed
Recommended: Python 3.10 or newer

Check your version:

```bash
python --version
```

If `python` does not work, try:

```bash
python3 --version
```

### 3. Optional: create a virtual environment

```bash
python -m venv .venv
```

Activate it on Windows:

```bash
.venv\Scripts\activate
```

Activate it on macOS / Linux:

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install numpy pandas matplotlib
```

If `pip` is not available, use:

```bash
python -m pip install numpy pandas matplotlib
```

### 5. Required packages for this report
- `numpy`
- `pandas`
- `matplotlib`

---

## Usage

### Run the analyzer
Open terminal in the `Anastasija_L-N` folder and run:

```bash
python buildReport.py input.csv output_file_name
```

### Input files
Keep CSV files in the `input` folder next to `buildReport.py`.

### Example

```bash
python buildReport.py input/SensorReading-v.csv ReportoPavadinimas
```

### Output
- `output/report.pdf` → Full analytical report  

The script creates an `output` folder next to `buildReport.py` automatically if it does not already exist.

### If you get `ModuleNotFoundError`
Example:

```text
ModuleNotFoundError: No module named 'pandas'
```

This means the required packages are not installed in the Python environment you are using.
Install them with:

```bash
python -m pip install numpy pandas matplotlib
```

Then run the script again.

---

## Technologies Used

### Backend / Analysis
- Python  
- pandas  
- numpy  
- matplotlib  

---

## Configuration

### Expected CSV format
Date, Temperature, CO2PPM, PressureHpa, HumidityPct

---

### Threshold settings
Thresholds are stored in `config.json` next to `buildReport.py`.

Default structure:

```json
{
  "thresholds": {
    "Temperature": { "low": null, "high": 30.0 },
    "CO2PPM": { "low": null, "high": 1000.0 },
    "PressureHpa": { "low": 980.0, "high": 1035.0 },
    "HumidityPct": { "low": 30.0, "high": 70.0 }
  }
}
```

Optional custom config path:

```bash
python buildReport.py input/SensorReading-v.csv ReportoPavadinimas --config custom-config.json
```

---

## Summary
Raw sensor CSV → Analysis → PDF report

---

## Author
GitHub: https://github.com/analicm
