APP_TITLE = "MarketLens"
APP_SUBTITLE = "Equity Intelligence Dashboard"

# ── Fundamental metrics available for charting ──────────────────────────────
METRICS = {
    "Market Cap": {
        "key": "marketCap",
        "source": "info",
        "format": "currency_b",
        "description": "Total market value of outstanding shares",
    },
    "Revenue": {
        "key": "TotalRevenue",
        "source": "financials",
        "format": "currency_b",
        "description": "Total revenue (annual)",
    },
    "Net Income": {
        "key": "NetIncome",
        "source": "financials",
        "format": "currency_b",
        "description": "Profit after all expenses and taxes",
    },
    "Free Cash Flow": {
        "key": "FreeCashFlow",
        "source": "cashflow",
        "format": "currency_b",
        "description": "Operating cash flow minus capex",
    },
    "Gross Profit": {
        "key": "GrossProfit",
        "source": "financials",
        "format": "currency_b",
        "description": "Revenue minus cost of goods sold",
    },
    "Operating Income": {
        "key": "OperatingIncome",
        "source": "financials",
        "format": "currency_b",
        "description": "Profit from core operations",
    },
    "EPS (TTM)": {
        "key": "trailingEps",
        "source": "info",
        "format": "currency",
        "description": "Earnings per share (trailing twelve months)",
    },
    "P/E Ratio": {
        "key": "trailingPE",
        "source": "info",
        "format": "ratio",
        "description": "Price-to-earnings ratio",
    },
    "P/B Ratio": {
        "key": "priceToBook",
        "source": "info",
        "format": "ratio",
        "description": "Price-to-book ratio",
    },
    "Debt-to-Equity": {
        "key": "debtToEquity",
        "source": "info",
        "format": "ratio",
        "description": "Financial leverage indicator",
    },
    "Return on Equity": {
        "key": "returnOnEquity",
        "source": "info",
        "format": "percent",
        "description": "Net income / shareholders' equity",
    },
    "Return on Assets": {
        "key": "returnOnAssets",
        "source": "info",
        "format": "percent",
        "description": "Net income / total assets",
    },
    "Profit Margin": {
        "key": "profitMargins",
        "source": "info",
        "format": "percent",
        "description": "Net income / revenue",
    },
    "Revenue Growth (YoY)": {
        "key": "revenueGrowth",
        "source": "info",
        "format": "percent",
        "description": "Year-over-year revenue growth rate",
    },
    "Dividend Yield": {
        "key": "dividendYield",
        "source": "info",
        "format": "percent",
        "description": "Annual dividend / share price",
    },
}

# Metrics that come from annual financial statements (not info dict)
STATEMENT_METRICS = {"Revenue", "Net Income", "Free Cash Flow", "Gross Profit", "Operating Income"}

# ── Popular stocks for autocomplete suggestions ───────────────────────────
POPULAR_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "JPM", "V", "UNH", "XOM", "JNJ", "WMT", "MA", "PG", "HD", "CVX",
    "MRK", "ABBV", "LLY", "PEP", "KO", "AVGO", "COST", "MCD", "TMO",
    "ACN", "CRM", "BAC", "DHR", "NEE", "ADBE", "TXN", "AMD", "NFLX",
    "QCOM", "PM", "BMY", "AMGN", "RTX", "INTC", "INTU", "SBUX",
    "GS", "BLK", "SPGI", "CAT", "DE", "GE", "BA", "MMM",
]

# ── Chart colours ─────────────────────────────────────────────────────────
COLOR_PRIMARY   = "#00D4AA"
COLOR_SECONDARY = "#FF6B6B"
COLOR_NEUTRAL   = "#A0AEC0"
COLOR_BG        = "#0D1117"
COLOR_SURFACE   = "#161B22"
COLOR_BORDER    = "#30363D"

PLOTLY_TEMPLATE = "plotly_dark"
