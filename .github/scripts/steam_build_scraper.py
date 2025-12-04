import os
import json
import pandas as pd
import requests
from datetime import datetime
from collections import OrderedDict

# --- CONFIG ---
CSV_SOURCE = "resources/builds.csv"
JSON_OUT = "resources/temp.json"

PATCH_KEYWORDS = ["patch", "version", "hotfix"]

def format_date_ordinal(ts):
    dt = datetime.utcfromtimestamp(ts)
    day = dt.day
    suffix = 'th' if 11 <= day <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(day % 10, 'th')
    return dt.strftime(f"%B {day}{suffix}, %Y")

def is_patch_note(item):
    """Return True if this news item looks like a patch note."""
    title = (item.get("title") or "").lower()
    feedlabel = (item.get("feedlabel") or "").lower()
    contents = (item.get("contents") or "").lower()
    tags = [t.lower() for t in item.get("tags", [])]

    # Check feedlabel, title keywords, "patch notes" in contents, or tags
    if any(k in feedlabel for k in PATCH_KEYWORDS):
        return True
    if any(k in title for k in PATCH_KEYWORDS):
        return True
    if "patch notes" in contents:
        return True
    if "patchnotes" in tags:
        return True
    return False

def fetch_latest_patch(appid):
    url = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
    try:
        r = requests.get(url, params={"appid": appid, "count": 50}, timeout=15)
        r.raise_for_status()
        newsitems = r.json().get("appnews", {}).get("newsitems", [])
    except Exception as e:
        print(f"[Steam News error] {appid}: {e}")
        return None

    # --- Step 1: keep only Steam Community posts ---
    community_posts = [
        item for item in newsitems
        if "steam_community_announcements" in (item.get("feedname") or "").lower()
    ]

    if not community_posts:
        return None

    # --- Step 2: filter patch-note-like posts among those ---
    patches = [item for item in community_posts if is_patch_note(item)]

    if not patches:
        return None

    # Pick the latest by date
    latest = max(patches, key=lambda x: x.get("date", 0))
    timestamp = latest.get("date", 0)
    return {
        "title": latest.get("title"),
        "url": latest.get("url"),
        "date": format_date_ordinal(timestamp),
        "timestamp": timestamp,
        "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/",
        "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg"
    }

# --- MAIN EXECUTION ---
df = pd.read_csv(CSV_SOURCE)
appids = df["appid"].dropna().astype(int).unique()

results = {}

for appid in appids:
    print(f"Checking app {appid}")
    patch_data = fetch_latest_patch(appid)

    if patch_data:
        results[str(appid)] = patch_data
        print(f"  Latest patch: {patch_data['title']} ({patch_data['date']})")
    else:
        print("  No Steam Community patch-note-style news found")
        results[str(appid)] = {
            "title": None,
            "url": None,
            "date": None,
            "timestamp": 0,
            "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/",
            "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg"
        }

# --- Sort results by timestamp descending (newest first) ---
sorted_results = sorted(
    results.items(),
    key=lambda x: x[1]["timestamp"] or 0,
    reverse=True
)
ordered_results = OrderedDict(sorted_results)

# --- Write JSON output ---
os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(ordered_results, f, ensure_ascii=False, indent=2)

print(f"Wrote {JSON_OUT}")
