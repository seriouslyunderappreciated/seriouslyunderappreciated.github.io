import os
import json
import pandas as pd
import requests
from datetime import datetime
from collections import OrderedDict

# --- CONFIG ---
CSV_SOURCE = "resources/builds.csv"
JSON_OUT = "resources/temp.json"

def format_date_ordinal(ts: int) -> str:
    dt = datetime.utcfromtimestamp(ts)
    day = dt.day
    suffix = 'th' if 11 <= day <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(day % 10, 'th')
    return dt.strftime(f"%B {day}{suffix}, %Y")

def get_latest_public_build(appid: int) -> dict | None:
    """Fetch latest public build info from SteamCMD API."""
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return None

    appid_str = str(appid)
    try:
        public_branch = data['data'][appid_str]['depots']['branches']['public']
        buildid = public_branch['buildid']
        timeupdated = int(public_branch['timeupdated'])
        return {
            "buildid": str(buildid),
            "date": format_date_ordinal(timeupdated)
        }
    except KeyError:
        return None

# --- MAIN EXECUTION ---
df = pd.read_csv(CSV_SOURCE)
appids = df["appid"].dropna().astype(int).unique()

results = {}

for appid in appids:
    build_info = get_latest_public_build(appid)
    
    if build_info:
        results[str(appid)] = {
            "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg",
            "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/",
            "buildid": build_info["buildid"],
            "date": build_info["date"]
        }
    else:
        results[str(appid)] = {
            "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg",
            "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/",
            "buildid": None,
            "date": None
        }

# --- Sort results by newest build date (timestamp descending) ---
sorted_results = sorted(
    results.items(),
    key=lambda x: pd.to_datetime(x[1]["date"]) if x[1]["date"] else pd.Timestamp(0),
    reverse=True
)
ordered_results = OrderedDict(sorted_results)

# --- Write JSON output ---
os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
with open(JSON_OUT, "w", encoding="utf-8") as f:
    json.dump(ordered_results, f, ensure_ascii=False, indent=2)
