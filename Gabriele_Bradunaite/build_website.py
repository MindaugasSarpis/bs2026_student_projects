import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv("SamplePortfolio.csv")
esg_cols = ["esg_Environmental","esg_Governance","esg_Social","esg_Sustainability","esg_Controversy"]
df["esg_avg"] = df[esg_cols].mean(axis=1)
controversy_cols = ["has_Tobacco","has_Alcohol","has_Gambling","has_Military","has_Fossil Fuels"]
avg_esg = df["esg_avg"].mean()
top_sector = df["sector"].value_counts().index[0]
top_country = df["geography"].value_counts().index[0]
flagged_count = df[df[controversy_cols].any(axis=1)].shape[0]
top10 = df[["NAME","TICKER","esg_avg","sector","geography","PRICE","CURRENCY"]].sort_values("esg_avg",ascending=False).head(10)
flagged_df = df[df[controversy_cols].any(axis=1)][["NAME","TICKER","sector","geography"]+controversy_cols]

table_rows = ""
for _, row in top10.iterrows():
    table_rows += f"""<tr onclick="showPopup('{row['TICKER']}','{row['NAME']}','Sector:{row['sector']}|Country:{row['geography']}|Price:{row['CURRENCY']} {row['PRICE']:.2f}|ESG:{row['esg_avg']:.1f}/10')" style="cursor:pointer"><td>{row['TICKER']}</td><td>{row['NAME']}</td><td>{row['sector']}</td><td>{row['geography']}</td><td><span class="score">{row['esg_avg']:.1f}</span></td></tr>"""

flagged_rows = ""
for _, row in flagged_df.iterrows():
    flags = [c.replace("has_","") for c in controversy_cols if row[c]==True]
    badges = "".join([f'<span class="badge">{f}</span>' for f in flags])
    flagged_rows += f"<tr><td>{row['TICKER']}</td><td>{row['NAME']}</td><td>{row['sector']}</td><td>{row['geography']}</td><td>{badges}</td></tr>"

print("Chunk 1 done!")
html_top = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Portfolio Analysis</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',sans-serif;background:#0a0a0f;color:#e0e0e0}
nav{background:#0d0d18;border-bottom:1px solid #ffffff15;padding:0 40px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100}
.nav-logo{color:#fff;font-weight:900;font-size:18px;padding:20px 0}
.nav-logo span{color:#e94560}
.nav-links{display:flex;gap:4px}
.nav-links button{background:none;border:none;color:#6b6b80;font-size:14px;font-weight:600;padding:8px 16px;border-radius:8px;cursor:pointer;font-family:'Inter',sans-serif}
.nav-links button:hover{color:#fff;background:#ffffff10}
.nav-links button.active{color:#e94560;background:#e9456020}
.page{display:none}
.page.active{display:block}
.hero{background:linear-gradient(135deg,#0a0a0f,#1a1a2e,#16213e);padding:80px 40px;text-align:center;border-bottom:1px solid #ffffff15}
.hero-tag{display:inline-block;background:#e9456020;border:1px solid #e9456050;color:#e94560;padding:6px 18px;border-radius:50px;font-size:12px;font-weight:600;letter-spacing:2px;text-transform:uppercase;margin-bottom:24px}
.hero h1{font-size:52px;font-weight:900;color:#fff;margin-bottom:16px}
.hero p{color:#6b6b80;font-size:16px;max-width:500px;margin:0 auto 32px}
.hero-buttons{display:flex;gap:12px;justify-content:center}
.hero-btn{padding:12px 24px;border-radius:10px;font-size:14px;font-weight:600;cursor:pointer;border:none;font-family:'Inter',sans-serif;transition:all 0.2s}
.hero-btn.primary{background:#e94560;color:white}
.hero-btn.primary:hover{background:#c73652;transform:translateY(-2px)}
.hero-btn.secondary{background:#ffffff10;color:#fff;border:1px solid #ffffff20}
.hero-btn.secondary:hover{background:#ffffff20;transform:translateY(-2px)}
.container{max-width:1100px;margin:0 auto;padding:60px 40px}
.section-title{font-size:11px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:#e94560;margin-bottom:12px}
.section-heading{font-size:32px;font-weight:800;color:#fff;margin-bottom:40px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;margin-bottom:70px}
.stat-card{background:#12121a;border:1px solid #ffffff10;border-radius:16px;padding:28px;text-align:center;transition:all 0.3s;cursor:pointer}
.stat-card:hover{border-color:#e94560;transform:translateY(-6px);box-shadow:0 20px 40px rgba(233,69,96,0.15)}
.stat-card .number{font-size:40px;font-weight:900;color:#4ade80;margin-bottom:8px}
.stat-card .label{font-size:13px;color:#6b6b80;font-weight:600;text-transform:uppercase;letter-spacing:1px}
.chart-card{background:#12121a;border:1px solid #ffffff10;border-radius:16px;overflow:hidden;margin-bottom:40px}
.chart-card img{width:100%;display:block}
.chart-caption{padding:20px 24px;border-top:1px solid #ffffff10}
.chart-caption p{color:#6b6b80;font-size:14px;line-height:1.6}
table{width:100%;border-collapse:collapse;background:#12121a;border-radius:16px;overflow:hidden;margin-bottom:60px}
th{background:#1a1a2e;color:#e94560;font-size:11px;letter-spacing:2px;text-transform:uppercase;padding:16px 20px;text-align:left}
td{padding:14px 20px;border-top:1px solid #ffffff08;color:#a0a0b0;font-size:14px}
tr:hover td{background:#ffffff05;color:#fff}
.score{background:#4ade8020;color:#4ade80;padding:4px 12px;border-radius:20px;font-weight:700;font-size:13px}
.badge{background:#e9456020;color:#e94560;border:1px solid #e9456040;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;margin-right:4px;display:inline-block;margin-bottom:4px}
.esg-bars{display:flex;flex-direction:column;gap:20px;margin-bottom:60px}
.esg-bar-item{background:#12121a;border:1px solid #ffffff10;border-radius:12px;padding:20px 24px}
.esg-bar-label{display:flex;justify-content:space-between;margin-bottom:10px}
.esg-bar-label span:first-child{color:#fff;font-weight:600;font-size:15px}
.esg-bar-label span:last-child{color:#4ade80;font-weight:700;font-size:15px}
.esg-bar-track{background:#ffffff10;border-radius:999px;height:10px;overflow:hidden}
.esg-bar-fill{height:100%;border-radius:999px;background:linear-gradient(90deg,#4ade80,#22d3ee);transition:width 1s ease}
.popup-overlay{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:1000;justify-content:center;align-items:center}
.popup-overlay.open{display:flex}
.popup{background:#12121a;border:1px solid #ffffff20;border-radius:20px;padding:40px;max-width:480px;width:90%;position:relative}
.popup h3{font-size:22px;font-weight:800;color:#fff;margin-bottom:8px}
.popup .ticker{color:#e94560;font-size:13px;font-weight:700;letter-spacing:2px;text-transform:uppercase;margin-bottom:24px}
.popup-detail{display:flex;justify-content:space-between;padding:12px 0;border-bottom:1px solid #ffffff10}
.popup-detail:last-of-type{border-bottom:none}
.popup-detail span:first-child{color:#6b6b80;font-size:14px}
.popup-detail span:last-child{color:#fff;font-weight:600;font-size:14px}
.popup-close{position:absolute;top:16px;right:20px;background:none;border:none;color:#6b6b80;font-size:24px;cursor:pointer}
.conclusions{background:#12121a;border:1px solid #ffffff10;border-radius:16px;padding:40px;margin-bottom:60px}
.conclusion-item{display:flex;gap:16px;margin-bottom:20px;align-items:flex-start}
.bullet{width:8px;height:8px;border-radius:50%;background:#e94560;margin-top:6px;flex-shrink:0}
.conclusion-item p{color:#a0a0b0;font-size:15px;line-height:1.7}
.conclusion-item strong{color:#fff}
footer{border-top:1px solid #ffffff10;padding:30px 40px;text-align:center;color:#3a3a4a;font-size:13px}
</style></head><body>"""

print("Chunk 2 done!")
html_bottom = f"""
<nav>
<div class="nav-logo">Portfolio<span>.</span>AI</div>
<div class="nav-links">
<button class="active" onclick="showPage('home',this)">Home</button>
<button onclick="showPage('esg',this)">ESG Analysis</button>
<button onclick="showPage('top10',this)">Top Companies</button>
<button onclick="showPage('controversial',this)">Controversial</button>
</div></nav>
<div class="popup-overlay" id="popup-overlay" onclick="closePopup(event)">
<div class="popup">
<button class="popup-close" onclick="document.getElementById('popup-overlay').classList.remove('open')">x</button>
<div class="ticker" id="popup-ticker"></div>
<h3 id="popup-name"></h3>
<div id="popup-details"></div>
</div></div>
<div class="page active" id="page-home">
<div class="hero"><div class="hero-tag">Data Analysis Project</div><h1>Portfolio Analysis</h1>
<p>ESG screening, sector and geographic breakdown of {len(df)} real investments.</p>
<div class="hero-buttons">
<button class="hero-btn primary" onclick="showPage('esg',document.querySelectorAll('.nav-links button')[1])">View ESG Analysis</button>
<button class="hero-btn secondary" onclick="showPage('controversial',document.querySelectorAll('.nav-links button')[3])">Controversial Holdings</button>
</div></div>
<div class="container">
<p class="section-title">Overview</p><h2 class="section-heading">Key Numbers</h2>
<div class="stats">
<div class="stat-card" onclick="showPage('top10',document.querySelectorAll('.nav-links button')[2])"><div class="number">{len(df)}</div><div class="label">Total Investments</div></div>
<div class="stat-card" onclick="showPage('esg',document.querySelectorAll('.nav-links button')[1])"><div class="number">{avg_esg:.1f}</div><div class="label">Avg ESG Score</div></div>
<div class="stat-card" onclick="showPage('controversial',document.querySelectorAll('.nav-links button')[3])"><div class="number">{flagged_count}</div><div class="label">Flagged Holdings</div></div>
<div class="stat-card"><div class="number">{df['geography'].nunique()}</div><div class="label">Countries</div></div>
</div>
<p class="section-title">Sectors</p><h2 class="section-heading">Investment by Sector</h2>
<div class="chart-card"><img src="chart_sectors.png"><div class="chart-caption"><p>Top 10 sectors in the portfolio.</p></div></div>
<p class="section-title">Geography</p><h2 class="section-heading">Investment by Country</h2>
<div class="chart-card"><img src="chart_geography.png"><div class="chart-caption"><p>Top 10 countries by number of holdings.</p></div></div>
<p class="section-title">Analysis</p><h2 class="section-heading">Conclusions</h2>
<div class="conclusions">
<div class="conclusion-item"><div class="bullet"></div><p>The portfolio contains <strong>{len(df)} investments</strong> across {df['geography'].nunique()} countries and {df['sector'].nunique()} sectors.</p></div>
<div class="conclusion-item"><div class="bullet"></div><p>The most represented sector is <strong>{top_sector}</strong>.</p></div>
<div class="conclusion-item"><div class="bullet"></div><p>Largest geographic exposure is to <strong>{top_country}</strong>.</p></div>
<div class="conclusion-item"><div class="bullet"></div><p><strong>{flagged_count} holdings</strong> were flagged for controversial activities.</p></div>
<div class="conclusion-item"><div class="bullet"></div><p>Average ESG score is <strong>{avg_esg:.1f} out of 10</strong>.</p></div>
</div></div></div>
<div class="page" id="page-esg">
<div class="hero"><div class="hero-tag">ESG Analysis</div><h1>Sustainability Scores</h1><p>How ethical are the investments in this portfolio?</p></div>
<div class="container">
<p class="section-title">Score Breakdown</p><h2 class="section-heading">Average ESG by Category</h2>
<div class="esg-bars">
<div class="esg-bar-item"><div class="esg-bar-label"><span>Environmental</span><span>{df['esg_Environmental'].mean():.1f} / 10</span></div><div class="esg-bar-track"><div class="esg-bar-fill" style="width:{df['esg_Environmental'].mean()*10:.1f}%"></div></div></div>
<div class="esg-bar-item"><div class="esg-bar-label"><span>Governance</span><span>{df['esg_Governance'].mean():.1f} / 10</span></div><div class="esg-bar-track"><div class="esg-bar-fill" style="width:{df['esg_Governance'].mean()*10:.1f}%"></div></div></div>
<div class="esg-bar-item"><div class="esg-bar-label"><span>Social</span><span>{df['esg_Social'].mean():.1f} / 10</span></div><div class="esg-bar-track"><div class="esg-bar-fill" style="width:{df['esg_Social'].mean()*10:.1f}%"></div></div></div>
<div class="esg-bar-item"><div class="esg-bar-label"><span>Sustainability</span><span>{df['esg_Sustainability'].mean():.1f} / 10</span></div><div class="esg-bar-track"><div class="esg-bar-fill" style="width:{df['esg_Sustainability'].mean()*10:.1f}%"></div></div></div>
<div class="esg-bar-item"><div class="esg-bar-label"><span>Controversy</span><span>{df['esg_Controversy'].mean():.1f} / 10</span></div><div class="esg-bar-track"><div class="esg-bar-fill" style="width:{df['esg_Controversy'].mean()*10:.1f}%"></div></div></div>
</div>
<div class="chart-card"><img src="chart_esg.png"><div class="chart-caption"><p>Visual comparison of all 5 ESG categories across the portfolio.</p></div></div>
</div></div>
<div class="page" id="page-top10">
<div class="hero"><div class="hero-tag">Top Companies</div><h1>Best ESG Performers</h1><p>Click any row to see details.</p></div>
<div class="container">
<p class="section-title">Rankings</p><h2 class="section-heading">Top 10 ESG Companies</h2>
<table><tr><th>Ticker</th><th>Company</th><th>Sector</th><th>Country</th><th>ESG Score</th></tr>
{table_rows}
</table></div></div>
<div class="page" id="page-controversial">
<div class="hero"><div class="hero-tag">Controversial Holdings</div><h1>Flagged Investments</h1><p>{flagged_count} holdings flagged for tobacco, alcohol, gambling, military or fossil fuels.</p></div>
<div class="container">
<p class="section-title">Flagged</p><h2 class="section-heading">All Controversial Companies</h2>
<table><tr><th>Ticker</th><th>Company</th><th>Sector</th><th>Country</th><th>Flags</th></tr>
{flagged_rows}
</table></div></div>
<footer>Data Analysis and Artificial Intelligence &mdash; Dr. Mindaugas Sarpis &mdash; 2026</footer>
<script>
function showPage(id,btn){{document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));document.querySelectorAll('.nav-links button').forEach(b=>b.classList.remove('active'));document.getElementById('page-'+id).classList.add('active');if(btn)btn.classList.add('active');window.scrollTo(0,0);}}
function showPopup(ticker,name,details){{document.getElementById('popup-ticker').textContent=ticker;document.getElementById('popup-name').textContent=name;const parts=details.split('|');let html='';parts.forEach(p=>{{const[l,...v]=p.split(':');html+=`<div class="popup-detail"><span>${{l}}</span><span>${{v.join(':')}}</span></div>`;}});document.getElementById('popup-details').innerHTML=html;document.getElementById('popup-overlay').classList.add('open');}}
function closePopup(e){{if(e.target===document.getElementById('popup-overlay'))document.getElementById('popup-overlay').classList.remove('open');}}
</script></body></html>"""

with open('index.html','w',encoding='utf-8') as f:
    f.write(html_top + html_bottom)

print("Website done! Open index.html in your browser!")
