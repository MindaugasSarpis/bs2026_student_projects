# Arturas Sotnicenko - Data Analytics Workspace

This folder contains a minimal data analytics setup with a devcontainer, dependencies, and a starter notebook.

## Quick start

1. Open this folder in VS Code: `Arturas_Sotnicenko`.
2. Reopen in container when prompted.
3. Open the starter notebook and run the cells.

## Contents

- `.devcontainer/devcontainer.json` - Devcontainer configuration.
- `requirements.txt` - Python dependencies.
- `notebooks/starter.ipynb` - Starter analysis notebook.
- `macro_indicator_pipeline.py` (project root) - Builds indicator index + source coverage tables and flags missing dataset codes/keys.

## Indicator Coverage Pipeline

Build indicator/source coverage files:

```bash
python macro_indicator_pipeline.py \
  --country-code LT \
  --outdir bs2026_student_projects/Arturas_Sotnicenko/outputs
```

Notebook usage:

```python
from macro_indicator_pipeline import run, stream_resolved_sources

results = run(country_code="LT", outdir="bs2026_student_projects/Arturas_Sotnicenko/outputs")
display(results["indicator_index"])
display(results["coverage"].head(20))
display(results["missing_queue"].head(20))

# Replacement for notebook cell 6 (resolve + stream currently resolved endpoints):
stream = stream_resolved_sources(country_code="LT", coverage=results["coverage"])
display(stream["endpoint_status_df"])
# Example loaded dataset:
first_key = next(iter(stream["normalized_sources"]))
display(stream["normalized_sources"][first_key].head())
```
