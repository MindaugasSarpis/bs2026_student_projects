from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

OUT = "project_report.pdf"

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "title", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=22, leading=26, alignment=0, spaceAfter=4,
)
subtitle_style = ParagraphStyle(
    "subtitle", parent=styles["Normal"], fontName="Helvetica",
    fontSize=10.5, textColor=colors.HexColor("#444444"), spaceAfter=10,
)
h2_style = ParagraphStyle(
    "h2", parent=styles["Heading2"], fontName="Helvetica-Bold",
    fontSize=13, leading=16, spaceBefore=12, spaceAfter=6,
    textColor=colors.HexColor("#1a1a1a"),
)
body_style = ParagraphStyle(
    "body", parent=styles["BodyText"], fontName="Helvetica",
    fontSize=10, leading=14, alignment=4, spaceAfter=6,  # justified
)
bullet_style = ParagraphStyle(
    "bullet", parent=body_style, leftIndent=14, bulletIndent=2, spaceAfter=2,
)
footer_style = ParagraphStyle(
    "footer", parent=styles["Normal"], fontName="Helvetica",
    fontSize=8.5, textColor=colors.HexColor("#666666"),
)

doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=18*mm, bottomMargin=18*mm,
    title="OSRS Grand Exchange Price Tracker",
    author="Tomas Kondrotas",
)

story = []

story.append(Paragraph("OSRS Grand Exchange Price Tracker", title_style))
story.append(Paragraph("Tomas Kondrotas | BS2026 Data Analysis Course | April 2026", subtitle_style))
story.append(HRFlowable(width="100%", thickness=0.8, color=colors.HexColor("#888888")))
story.append(Spacer(1, 6))

story.append(Paragraph("Project Overview", h2_style))
story.append(Paragraph(
    "This project is a web application that <b>visualizes Old School RuneScape (OSRS) Grand Exchange (GE) market "
    "data</b>. The GE is the in-game marketplace where players buy and sell over 4,000 tradeable items, with prices "
    "fluctuating based on supply and demand. The app pulls live pricing data from the community-run OSRS Wiki Prices "
    "API and presents it through four focused views: an item browser, a high-alchemy profit calculator, a "
    "flip-opportunity ranker, and a per-item price history chart. The goal is to make it easy to spot profitable "
    "trades at a glance rather than scrolling through raw numbers in the game client.",
    body_style,
))

story.append(Paragraph("Dataset", h2_style))
story.append(Paragraph(
    "The underlying dataset is the full OSRS item mapping (~4,500 tradeable items) plus four live price feeds exposed "
    "by <font face='Courier'>prices.runescape.wiki</font>: <font face='Courier'>latest</font> (current instant "
    "buy/sell), <font face='Courier'>5m</font> and <font face='Courier'>1h</font> (rolling averages and volume), and "
    "<font face='Courier'>timeseries</font> (historical prices at 5-minute, 1-hour, 6-hour, and 24-hour resolutions, "
    "up to one year back). Item metadata includes name, examine text, members-only flag, high-alch value, and the "
    "4-hour GE buy limit. The item mapping is cached locally for 24 hours "
    "(<font face='Courier'>mapping_cache.json</font>) to avoid hammering the API.",
    body_style,
))

story.append(Paragraph("Key Features", h2_style))

table_data = [
    [Paragraph("<b>Feature</b>", body_style), Paragraph("<b>Description</b>", body_style)],
    [Paragraph("Browse", body_style),
     Paragraph("Searchable grid of all ~4,500 tradeable items with scraped item sprites.", body_style)],
    [Paragraph("High Alch", body_style),
     Paragraph("Sortable table showing buy price vs. high-alch value, with profit/loss highlighted in green/red.", body_style)],
    [Paragraph("Flip Picks", body_style),
     Paragraph("Top 10 flip opportunities ranked by a composite score (margin % &#215; log(volume) &#215; log(max profit)).", body_style)],
    [Paragraph("Item Detail", body_style),
     Paragraph("Live prices, 5-minute and 1-hour averages, volume stats, and an interactive price history chart (5m / 1h / 6h / 24h timesteps).", body_style)],
    [Paragraph("Icon scraper", body_style),
     Paragraph("One-time script that downloads ~4,500 item sprites from the OSRS Wiki into <font face='Courier'>images/</font>.", body_style)],
]
tbl = Table(table_data, colWidths=[35*mm, 130*mm])
tbl.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f4f4")]),
]))
story.append(tbl)

story.append(Paragraph("Flipping Methodology &amp; Honest Results", h2_style))
story.append(Paragraph(
    "&quot;Flipping&quot; in OSRS means buying an item at the instant-buy low price and reselling at the instant-sell "
    "high price, pocketing the margin. The <font face='Courier'>/api/flips</font> endpoint filters the full item list "
    "down to tradeable candidates where:",
    body_style,
))
for b in [
    "<font face='Courier'>sell &gt; buy</font> and margin &#8805; 1% (discards noise)",
    "<font face='Courier'>buy &#8805; 100 gp</font> (ignores junk items)",
    "1-hour combined volume &#8805; 10 (ensures the item actually trades)",
]:
    story.append(Paragraph(b, bullet_style, bulletText="\u2022"))
story.append(Spacer(1, 4))
story.append(Paragraph(
    "Each candidate is then scored by <font face='Courier'>margin_pct &#215; log1p(volume) &#215; "
    "log1p(max_profit)</font>, which rewards three axes at once: percentage margin, liquidity, and absolute profit "
    "ceiling (margin &#215; 4-hour buy limit). The top 10 are returned.",
    body_style,
))
story.append(Paragraph(
    "<b>Reality check.</b> Running this manually, I was only able to complete a handful of flips and earn roughly "
    "<b>9,000 gp total</b> &mdash; trivial by OSRS standards. The core problem is that the API data lags real market "
    "movement by minutes, and the most profitable flips are claimed by bots and faster players long before a human "
    "can place an offer. To be genuinely profitable, the flipping loop would need to be automated: continuously poll "
    "the API, auto-place buy/sell offers via a client-side macro or bot, and cancel stale offers. As a manual tool, "
    "Flip Picks is useful for learning which items are moving, but <b>unreliable as an income strategy</b>.",
    body_style,
))

story.append(Paragraph("Visualizations", h2_style))
story.append(Paragraph("The app produces the following views and visualizations:", body_style))
for i, item in enumerate([
    "<b>Item grid</b> (Browse) &mdash; paginated sprite grid with debounced search filter",
    "<b>High-alch profit table</b> &mdash; sortable by profit, green rows = profitable, red = loss",
    "<b>Flip leaderboard</b> &mdash; ranked cards with margin, volume, 4-hour limit, and composite score",
    "<b>Live price card</b> &mdash; instant buy/sell prices with timestamps",
    "<b>Rolling averages panel</b> &mdash; 5-minute and 1-hour average prices and volumes",
    "<b>Interactive price history chart</b> &mdash; Chart.js line chart with selectable timesteps (5m/1h/6h/24h)",
], start=1):
    story.append(Paragraph(f"({i}) {item}", bullet_style, bulletText="\u2022"))

story.append(Paragraph("Tools and Methods", h2_style))
story.append(Paragraph(
    "<b>Language:</b> Python 3 &nbsp;|&nbsp; <b>Backend:</b> Flask &nbsp;|&nbsp; <b>Frontend:</b> vanilla "
    "HTML/CSS/JS, Chart.js with <font face='Courier'>date-fns</font> adapter &nbsp;|&nbsp; <b>HTTP client:</b> "
    "<font face='Courier'>requests</font> &nbsp;|&nbsp; <b>Data source:</b> OSRS Wiki Prices API &nbsp;|&nbsp; "
    "<b>Version control:</b> Git + GitHub",
    body_style,
))
story.append(Paragraph(
    "The app is intentionally dependency-light (only <font face='Courier'>flask</font> and "
    "<font face='Courier'>requests</font>). All rendering is done client-side from a thin Flask proxy that forwards "
    "API calls and caches the mapping. A separate one-shot scraper "
    "(<font face='Courier'>scrape_osrs_icons.py</font>) downloads item sprites from the OSRS Wiki on first setup.",
    body_style,
))

story.append(Paragraph("Conclusions", h2_style))
story.append(Paragraph(
    "The OSRS Grand Exchange generates a steady stream of public market data, and a small Flask app is enough to "
    "turn it into something useful: a clean browser, a high-alch profit screener, a flip ranker, and per-item price "
    "history. The visualizations make patterns that are invisible in the game client &mdash; margin, liquidity, "
    "historical trend &mdash; immediately readable.",
    body_style,
))
story.append(Paragraph(
    "The flipping feature in particular shows both the appeal and the limits of a manual tool. The composite score "
    "does surface real opportunities, and I was able to make a few flips for around 9,000 gp. But the margins are "
    "thin, the best trades are taken within seconds, and the human round-trip (open tab, read pick, switch to "
    "client, place offer) is too slow. The natural next step would be to automate the loop against the API &mdash; "
    "at which point the tool becomes an actual profit engine rather than a visualization exercise.",
    body_style,
))

doc.build(story)
print(f"Wrote {OUT}")
