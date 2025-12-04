import os
import json
import pandas as pd
import requests
from datetime import datetime
from collections import OrderedDict

# --- CONFIG ---
CSV_SOURCE = "resources/builds.csv"
JSON_OUT = "resources/temp.json"

def format_date_ordinal(ts):
    """Convert UNIX timestamp to formatted date with ordinal suffix."""
    dt = datetime.utcfromtimestamp(ts)
    day = dt.day
    suffix = 'th' if 11 <= day <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(day % 10, 'th')
    return dt.strftime(f"%B {day}{suffix}, %Y")

def fetch_app_info(appid):
    """Fetch app info from SteamCMD API and return relevant data."""
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    print(f"\nFetching info for app {appid} from {url}")
    
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        full_json = r.json()
        print(f"Raw JSON fetched for {appid}:\n{json.dumps(full_json, indent=2)[:1000]}...")  # preview first 1000 chars
        data = full_json.get("data", {})
    except Exception as e:
        print(f"[SteamCMD API error] {appid}: {e}")
        return None

    app_data = data.get(str(appid))
    if not app_data:
        print(f"[DEBUG] App {appid} not found inside 'data' key")
        return None

    branches = app_data.get("branches")
    if not branches:
        print(f"[DEBUG] App {appid} has no 'branches' key")
        return None

    public_branch = branches.get("public")
    if not public_branch:
        print(f"[DEBUG] App {appid} has no 'public' branch")
        return None

    buildid = public_branch.get("buildid")
    timeupdated = public_branch.get("timeupdated")

    if not buildid or not timeupdated:
        print(f"[DEBUG] App {appid} missing 'buildid' or 'timeupdated'")
        return None

    timeupdated = int(timeupdated)

    result = {
        "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg",
        "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/",
        "buildid": str(buildid),
        "date": format_date_ordinal(timeupdated),
        "timestamp": timeupdated  # used for sorting
    }
    
    print(f"[SUCCESS] App {appid} data: {result}")
    return result

# --- MAIN EXECUTION ---
df = pd.read_csv(CSV_SOURCE)
appids = df["appid"].dropna().astype(int).unique()

results = {}

for appid in appids:
    info = fetch_app_info(appid)
    if info:
        results[str(appid)] = info

# --- Sort results by timestamp descending (newest first) ---
sorted_results = sorted(
    results.items(),
    key=lambda x: x[1]["timestamp"],
    reverse=True
)
ordered_results = OrderedDict(sorted_results)

# --- Write JSON output ---
os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
with open(JSON_OUT, "w", encoding="utf-8") as f:
    # Remove timestamp from output since it's only used for sorting
    json.dump({k: {key: val for key, val in v.items() if key != "timestamp"} 
               for k, v in ordered_results.items()},
              f, ensure_ascii=False, indent=2)

print(f"\nWrote {JSON_OUT} with {len(ordered_results)} apps.")
