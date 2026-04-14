import os
import time
import urllib.parse
import requests

API_URL = "https://prices.runescape.wiki/api/v1/osrs/mapping"
IMAGE_BASE = "https://oldschool.runescape.wiki/images/"
OUTPUT_DIR = "images"

HEADERS = {
    "User-Agent": "osrs-icon-scraper/1.0 (personal project)"
}


def icon_to_url(icon_name: str, detail: bool = True) -> str:
    # Replace spaces with underscores
    name = icon_name.replace(" ", "_")
    # Optionally insert _detail before .png
    if detail and name.endswith(".png"):
        name = name[:-4] + "_detail.png"
    # URL-encode using UTF-8 (safe chars: alphanumerics, underscore, hyphen, dot)
    encoded = urllib.parse.quote(name, safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-.")
    return IMAGE_BASE + encoded


def fetch_image(url: str) -> requests.Response | None:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        return resp
    except requests.RequestException as e:
        print(f"ERROR: {url} — {e}")
        return None


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Fetching item list...")
    resp = requests.get(API_URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    items = resp.json()
    print(f"Found {len(items)} items.")

    seen_icons = set()
    skipped = 0
    downloaded = 0
    failed = 0

    for item in items:
        icon = item.get("icon", "")
        if not icon or icon in seen_icons:
            skipped += 1
            continue
        seen_icons.add(icon)

        filepath = os.path.join(OUTPUT_DIR, icon)
        if os.path.exists(filepath):
            skipped += 1
            continue

        # Try _detail variant first, then fall back to plain icon name
        for use_detail in (True, False):
            url = icon_to_url(icon, detail=use_detail)
            img_resp = fetch_image(url)
            if img_resp is None:
                failed += 1
                break
            if img_resp.status_code == 200:
                with open(filepath, "wb") as f:
                    f.write(img_resp.content)
                downloaded += 1
                suffix = "" if use_detail else " (no-detail fallback)"
                print(f"[{downloaded}] {icon}{suffix}")
                break
            if img_resp.status_code != 404 or not use_detail:
                # Non-404 error on detail try, or both attempts exhausted
                print(f"SKIP ({img_resp.status_code}): {url}")
                failed += 1
                break
            # 404 on _detail — loop continues to try plain name
            time.sleep(0.05)

        time.sleep(0.1)  # be polite to the wiki

    print(f"\nDone. Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")


if __name__ == "__main__":
    main()
