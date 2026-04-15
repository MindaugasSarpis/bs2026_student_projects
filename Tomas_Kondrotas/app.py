import json
import math
import os
import time
import requests
from flask import Flask, jsonify, render_template, send_from_directory

app = Flask(__name__)

MAPPING_CACHE_FILE = "mapping_cache.json"
MAPPING_CACHE_TTL = 60 * 60 * 24  # 24 hours

HEADERS = {
    "User-Agent": "osrs-ge-visualizer/1.0 (personal project)"
}


def get_mapping():
    if os.path.exists(MAPPING_CACHE_FILE):
        mtime = os.path.getmtime(MAPPING_CACHE_FILE)
        if time.time() - mtime < MAPPING_CACHE_TTL:
            with open(MAPPING_CACHE_FILE) as f:
                return json.load(f)

    resp = requests.get(
        "https://prices.runescape.wiki/api/v1/osrs/mapping",
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    with open(MAPPING_CACHE_FILE, "w") as f:
        json.dump(data, f)

    return data


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/alch")
def alch():
    return render_template("alch.html")


@app.route("/flips")
def flips():
    return render_template("flips.html")


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    return render_template("item.html", item_id=item_id)


@app.route("/api/mapping")
def api_mapping():
    return jsonify(get_mapping())


@app.route("/api/latest")
def api_latest():
    resp = requests.get(
        "https://prices.runescape.wiki/api/v1/osrs/latest",
        headers=HEADERS,
        timeout=30,
    )
    resp.raise_for_status()
    return jsonify(resp.json())


@app.route("/api/price/<int:item_id>")
def api_price(item_id):
    resp = requests.get(
        f"https://prices.runescape.wiki/api/v1/osrs/latest?id={item_id}",
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return jsonify(resp.json())


@app.route("/api/1h/<int:item_id>")
def api_1h(item_id):
    resp = requests.get(
        "https://prices.runescape.wiki/api/v1/osrs/1h",
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    item_data = data.get("data", {}).get(str(item_id))
    return jsonify({"data": item_data})


@app.route("/api/5m/<int:item_id>")
def api_5m(item_id):
    resp = requests.get(
        "https://prices.runescape.wiki/api/v1/osrs/5m",
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    item_data = data.get("data", {}).get(str(item_id))
    return jsonify({"data": item_data, "timestamp": data.get("timestamp")})


@app.route("/api/flips")
def api_flips():
    mapping_list = get_mapping()
    mapping = {str(item["id"]): item for item in mapping_list}

    latest_resp = requests.get(
        "https://prices.runescape.wiki/api/v1/osrs/latest",
        headers=HEADERS, timeout=20,
    )
    h1_resp = requests.get(
        "https://prices.runescape.wiki/api/v1/osrs/1h",
        headers=HEADERS, timeout=20,
    )
    latest_resp.raise_for_status()
    h1_resp.raise_for_status()

    latest = latest_resp.json().get("data", {})
    h1 = h1_resp.json().get("data", {})

    candidates = []
    for item_id, price in latest.items():
        buy = price.get("low")
        sell = price.get("high")
        if not buy or not sell or sell <= buy:
            continue

        meta = mapping.get(item_id, {})
        limit = meta.get("limit") or 1

        margin = sell - buy
        margin_pct = margin / buy * 100

        if margin_pct < 1 or buy < 100:
            continue

        h1_data = h1.get(item_id, {})
        vol_high = h1_data.get("highPriceVolume") or 0
        vol_low  = h1_data.get("lowPriceVolume")  or 0
        volume   = vol_high + vol_low

        if volume < 10:
            continue

        max_profit = margin * limit
        # score: margin % * log(volume) * log(max_profit+1)
        # rewards margin, liquidity, and absolute profit potential equally
        score = margin_pct * math.log1p(volume) * math.log1p(max_profit)

        candidates.append({
            "id": int(item_id),
            "name": meta.get("name", f"Item {item_id}"),
            "icon": meta.get("icon", ""),
            "members": meta.get("members", False),
            "examine": meta.get("examine", ""),
            "buy": buy,
            "sell": sell,
            "margin": margin,
            "margin_pct": round(margin_pct, 2),
            "volume_1h": volume,
            "limit": limit,
            "max_profit": max_profit,
            "score": round(score, 2),
        })

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return jsonify(candidates[:10])


@app.route("/api/timeseries/<int:item_id>/<timestep>")
def api_timeseries(item_id, timestep):
    if timestep not in ("5m", "1h", "6h", "24h"):
        return jsonify({"error": "invalid timestep"}), 400
    resp = requests.get(
        f"https://prices.runescape.wiki/api/v1/osrs/timeseries?id={item_id}&timestep={timestep}",
        headers=HEADERS,
        timeout=20,
    )
    resp.raise_for_status()
    return jsonify(resp.json())


@app.route("/images/<path:filename>")
def serve_image(filename):
    return send_from_directory("images", filename)


@app.route("/fonts/<path:filename>")
def serve_font(filename):
    return send_from_directory("fonts", filename)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
