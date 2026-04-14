# OSRS GE Tracker

A web app for tracking Old School RuneScape Grand Exchange prices, finding high-alch opportunities, and surfacing the best flip picks.

## Features

- **Browse** — search and browse all tradeable GE items with their icons
- **High Alch** — sortable table showing buy price vs. high alch value, with profit/loss highlighted
- **Flip Picks** — top 10 flip opportunities ranked by a composite score (margin × liquidity × max profit potential), refreshable on demand
- **Item Detail** — per-item price card with latest prices, 5-minute and 1-hour averages, volume stats, and an interactive price history chart (5m / 1h / 6h / 24h timesteps, up to 1-year range)

## Stack

- **Backend:** Python / Flask
- **Data source:** [OSRS Wiki Prices API](https://prices.runescape.wiki/osrs/guide/api) (mapping cached locally for 24 hours)
- **Charts:** Chart.js with the date-fns time adapter
- **Icons:** scraped item sprites served as static files

## Getting Started

1. Install dependencies:
   ```bash
   pip install flask requests
   ```

2. (Optional) Scrape item icons — only needed once:
   ```bash
   python scrape_osrs_icons.py
   ```

3. Run the app:
   ```bash
   python app.py
   ```

4. Open `http://localhost:5001` in your browser.

## Project Structure

```
app.py                  # Flask app and API proxy routes
scrape_osrs_icons.py    # One-time script to download item icons
mapping_cache.json      # Auto-generated item mapping cache (24h TTL)
images/                 # Item icon sprites
fonts/                  # RuneScape font files
templates/
  base.html             # Shared layout and navigation
  index.html            # Item browser
  alch.html             # High alch calculator
  flips.html            # Flip picks
  item.html             # Item detail with price chart
```