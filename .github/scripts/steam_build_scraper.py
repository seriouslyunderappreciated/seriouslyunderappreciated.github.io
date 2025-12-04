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
    """Format a UNIX timestamp as 'Month DayOrdinal, Year'."""
    dt = datetime.utcfromtimestamp(ts)
    day = dt.day
    suffix = 'th' if 11 <= day <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(day % 10, 'th')
    return dt.strftime(f"%B {day}{suffix}, %Y")

def fetch_app_info(appid):
    """Fetch info for an appid from SteamCMD API public branch."""
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[SteamCMD API error] {appid}: {e}")
        return None

    public_branch = data.get("branches", {}).get("public")
    if not public_branch:
        return None

    buildid = public_branch.get("buildid")
    timeupdated = public_branch.get("timeupdated", 0)

    if not buildid or timeupdated == 0:
        return None

    return {
        "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg",
        "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/",
        "buildid": buildid,
        "timestamp": timeupdated,
        "date": format_date_ordinal(timeupdated)
    }

# --- MAIN EXECUTION ---
df = pd.read_csv(CSV_SOURCE)
appids = df["appid"].dropna().astype(int).unique()

results = {}

for appid in appids:
    print(f"Checking app {appid}")
    app_data = fetch_app_info(appid)
    if app_data:
        results[str(appid)] = app_data
        print(f"  Build {app_data['buildid']} updated {app_data['date']}")
    else:
        print(f"  No public build info found for {appid}")

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
    json.dump(ordered_results, f, ensure_ascii=False, indent=2)

print(f"Wrote {JSON_OUT}")
