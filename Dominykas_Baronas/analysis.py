from __future__ import annotations

import numpy as np
import pandas as pd

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.ensemble import IsolationForest
    _SKLEARN = True
except ImportError:
    _SKLEARN = False

try:
    from scipy.stats import pearsonr
    _SCIPY = True
except ImportError:
    _SCIPY = False


def price_trend_analysis(price_df: pd.DataFrame, symbol: str) -> dict:
    if price_df.empty or len(price_df) < 30:
        return {"error": "Insufficient price data"}

    close  = price_df["Close"]
    daily  = close.pct_change().dropna()

    ytd_start = close[close.index >= f"{close.index[-1].year}-01-01"]
    ytd_ret   = (ytd_start.iloc[-1] / ytd_start.iloc[0] - 1) if len(ytd_start) > 1 else np.nan

    results = {
        "1M Return":        _pct(close.iloc[-1] / close.iloc[-22] - 1 if len(close) >= 22 else np.nan),
        "3M Return":        _pct(close.iloc[-1] / close.iloc[-66] - 1 if len(close) >= 66 else np.nan),
        "6M Return":        _pct(close.iloc[-1] / close.iloc[-126] - 1 if len(close) >= 126 else np.nan),
        "1Y Return":        _pct(close.iloc[-1] / close.iloc[-252] - 1 if len(close) >= 252 else np.nan),
        "YTD Return":       _pct(ytd_ret),
        "Annualised Vol":   _pct(daily.std() * np.sqrt(252))
    }

    if _SKLEARN:
        x = np.arange(len(close)).reshape(-1, 1)
        y = close.values
        lr = LinearRegression().fit(x, y)
        slope_pct = lr.coef_[0] / y[0] * 252
        results["Trend Signal"] = (
            f"▲ Uptrend (+{slope_pct*100:.1f}% annualised)" if slope_pct > 0.05
            else f"▼ Downtrend ({slope_pct*100:.1f}% annualised)" if slope_pct < -0.05
            else "→ Sideways / Neutral"
        )

    return results


def fundamental_health_score(info: dict) -> tuple[float, list[str]]:
    """
    Simple rule-based health score (0–100) with narrative bullets.
    Higher = healthier fundamentals.
    """
    score  = 50.0
    notes  = []

    pm = info.get("profitMargins")
    if pm is not None:
        if pm > 0.20:
            score += 10; notes.append("✅ Strong profit margin (>20%)")
        elif pm > 0.08:
            score += 5;  notes.append("🟡 Moderate profit margin (8–20%)")
        else:
            score -= 5;  notes.append("🔴 Thin profit margin (<8%)")

    de = info.get("debtToEquity")
    if de is not None:
        if de < 50:
            score += 8; notes.append("✅ Low leverage (D/E < 0.5)")
        elif de < 150:
            score += 2; notes.append("🟡 Moderate leverage (D/E 0.5–1.5)")
        else:
            score -= 8; notes.append("🔴 High leverage (D/E > 1.5)")

    rg = info.get("revenueGrowth")
    if rg is not None:
        if rg > 0.15:
            score += 10; notes.append("✅ Strong revenue growth (>15% YoY)")
        elif rg > 0:
            score += 4;  notes.append("🟡 Positive but slow revenue growth")
        else:
            score -= 6;  notes.append("🔴 Revenue declining YoY")

    pe = info.get("trailingPE")
    if pe is not None:
        if pe < 15:
            score += 7; notes.append("✅ Potentially undervalued (P/E < 15)")
        elif pe < 30:
            notes.append("🟡 Fair valuation range (P/E 15–30)")
        else:
            score -= 5; notes.append("🔴 High valuation (P/E > 30) — growth priced in")

    roe = info.get("returnOnEquity")
    if roe is not None:
        if roe > 0.20:
            score += 8; notes.append("✅ High ROE (>20%) — efficient capital use")
        elif roe > 0.10:
            score += 3; notes.append("🟡 Acceptable ROE (10–20%)")
        else:
            score -= 4; notes.append("🔴 Low ROE (<10%)")

    score = max(0, min(100, score))
    return round(score, 1), notes


def detect_anomalies(series: pd.Series) -> list[int]:
    if not _SKLEARN or series is None or len(series) < 5:
        return []

    X  = series.values.reshape(-1, 1)
    sc = StandardScaler()
    Xs = sc.fit_transform(X)

    iso = IsolationForest(contamination=0.2, random_state=42)
    preds = iso.fit_predict(Xs)
    return [series.index[i] for i, p in enumerate(preds) if p == -1]


def compare_price_stats(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    sym1: str,
    sym2: str,
) -> pd.DataFrame:
    rows = []

    def _stats(df, sym):
        if df.empty:
            return {}
        c     = df["Close"]
        daily = c.pct_change().dropna()
        return {
            "Symbol": sym,
            "1Y Return":      _pct(c.iloc[-1] / c.iloc[-252] - 1 if len(c) >= 252 else np.nan),
            "Ann. Volatility": _pct(daily.std() * np.sqrt(252))        }

    s1 = _stats(df1, sym1)
    s2 = _stats(df2, sym2)

    if not df1.empty and not df2.empty:
        r1 = df1["Close"].pct_change().dropna()
        r2 = df2["Close"].pct_change().dropna()
        common = pd.concat([r1.rename("a"), r2.rename("b")], axis=1).dropna()
        if len(common) > 60:

            if _SCIPY:
                corr, pval = pearsonr(common["a"], common["b"])
                s1["Return Corr"] = f"{corr:.3f} (p={pval:.3f})"
                s2["Return Corr"] = s1["Return Corr"]

    for s in [s1, s2]:
        rows.append(s)

    return pd.DataFrame(rows).set_index("Symbol").T if rows else pd.DataFrame()


def generate_ai_verdict(
    info1: dict,
    info2: dict,
    sym1: str,
    sym2: str,
    price_df1: pd.DataFrame,
    price_df2: pd.DataFrame,
) -> list[str]:
    verdicts = []

    pe1 = info1.get("trailingPE")
    pe2 = info2.get("trailingPE")
    if pe1 and pe2:
        cheaper = sym1 if pe1 < pe2 else sym2
        verdicts.append(
            f"💰 **Valuation**: {cheaper} trades at a lower P/E ratio "
            f"({min(pe1,pe2):.1f}x vs {max(pe1,pe2):.1f}x), suggesting it may be more attractively priced."
        )

    rg1 = info1.get("revenueGrowth")
    rg2 = info2.get("revenueGrowth")
    if rg1 is not None and rg2 is not None:
        faster = sym1 if rg1 > rg2 else sym2
        verdicts.append(
            f"🚀 **Revenue Growth**: {faster} is growing faster "
            f"({max(rg1,rg2)*100:.1f}% vs {min(rg1,rg2)*100:.1f}% YoY)."
        )

    pm1 = info1.get("profitMargins")
    pm2 = info2.get("profitMargins")
    if pm1 is not None and pm2 is not None:
        more_profitable = sym1 if pm1 > pm2 else sym2
        verdicts.append(
            f"📈 **Profitability**: {more_profitable} has higher profit margins "
            f"({max(pm1,pm2)*100:.1f}% vs {min(pm1,pm2)*100:.1f}%)."
        )

    de1 = info1.get("debtToEquity")
    de2 = info2.get("debtToEquity")
    if de1 is not None and de2 is not None:
        safer = sym1 if de1 < de2 else sym2
        verdicts.append(
            f"🛡️ **Balance Sheet**: {safer} carries less debt relative to equity "
            f"(D/E {min(de1,de2):.0f} vs {max(de1,de2):.0f})."
        )

    if not price_df1.empty and not price_df2.empty:
        c1 = price_df1["Close"]
        c2 = price_df2["Close"]
        ret1 = c1.iloc[-1] / c1.iloc[-252] - 1 if len(c1) >= 252 else None
        ret2 = c2.iloc[-1] / c2.iloc[-252] - 1 if len(c2) >= 252 else None
        if ret1 is not None and ret2 is not None:
            leader = sym1 if ret1 > ret2 else sym2
            verdicts.append(
                f"📊 **1Y Momentum**: {leader} has delivered stronger 1-year price returns "
                f"({max(ret1,ret2)*100:.1f}% vs {min(ret1,ret2)*100:.1f}%)."
            )

    roe1 = info1.get("returnOnEquity")
    roe2 = info2.get("returnOnEquity")
    if roe1 is not None and roe2 is not None:
        better_roe = sym1 if roe1 > roe2 else sym2
        verdicts.append(
            f"🏆 **Capital Efficiency**: {better_roe} generates higher returns on equity "
            f"({max(roe1,roe2)*100:.1f}% vs {min(roe1,roe2)*100:.1f}%)."
        )

    if not verdicts:
        verdicts.append("⚠️ Insufficient data to generate a meaningful comparison verdict.")

    return verdicts

def _pct(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v*100:+.2f}%"


def _ratio(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return f"{v:.2f}"
