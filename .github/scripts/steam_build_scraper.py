import os
import json
import pandas as pd
import requests
from datetime import datetime

# --- CONFIG ---
CSV_SOURCE = "resources/builds.csv"
JSON_OUT = "resources/temp.json"

PATCH_KEYWORDS = ["patch", "version", "hotfix"]

def format_date_ordinal(ts):
    dt = datetime.utcfromtimestamp(ts)
    day = dt.day
    suffix = 'th' if 11 <= day <= 13 else {1:'st',2:'nd',3:'rd'}.get(day % 10, 'th')
    return dt.strftime(f"%B {day}{suffix}, %Y")

def is_patch_note(item):
    """Return True if this news item looks like a patch note."""
    title = (item.get("title") or "").lower()
    feedlabel = (item.get("feedlabel") or "").lower()
    contents = (item.get("contents") or "").lower()

    # Check feedlabel, title keywords, or "patch notes" in contents
    if any(k in feedlabel for k in PATCH_KEYWORDS):
        return True
    if any(k in title for k in PATCH_KEYWORDS):
        return True
    if "patch notes" in contents:
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
    return {
        "title": latest.get("title"),
        "url": latest.get("url"),
        "date": format_date_ordinal(latest.get("date")),
        "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/"
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
            "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/"
        }

# --- Write JSON output ---
os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"Wrote {JSON_OUT}")
