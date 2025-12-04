import requests
import json
import csv
from pathlib import Path
from datetime import datetime

TEMP_JSON = Path("resources/temp.json")
BUILDS_CSV = Path("resources/builds.csv")

# Function to format date with ordinal suffix
def format_date_ordinal(ts: int) -> str:
    dt = datetime.utcfromtimestamp(ts)
    day = dt.day
    suffix = 'th' if 11 <= day <= 13 else {1:'st', 2:'nd', 3:'rd'}.get(day % 10, 'th')
    return dt.strftime(f"%B {day}{suffix}, %Y")

# Load existing builds.csv
existing_builds = {}
if BUILDS_CSV.exists():
    with open(BUILDS_CSV, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_builds[int(row['appid'])] = row['buildid']

# Example app IDs to fetch
APP_IDS = [
    1462040, 2909400, 1245620, 367520,
    1086940, 524220, 1113560, 814380
]

output_data = {}

for appid in APP_IDS:
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"Error fetching data for AppID {appid}: {e}")
        continue

    appid_str = str(appid)
    try:
        branch_info = data['data'][appid_str]['branches']['public']
        buildid = str(branch_info['buildid'])
        timeupdated = int(branch_info['timeupdated'])
    except KeyError:
        # No public build info
        continue

    # Skip if buildid matches builds.csv
    if existing_builds.get(appid) == buildid:
        continue

    # Format date with ordinal function
    formatted_date = format_date_ordinal(timeupdated)

    # Add entry
    output_data[appid] = {
        "steamheader": f"https://cdn.cloudflare.steamstatic.com/steam/apps/{appid}/header.jpg",
        "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes/",
        "date": formatted_date,
        "buildid": buildid
    }

# Sort by latest update
output_data_sorted = dict(
    sorted(
        output_data.items(),
        key=lambda x: x[1]['date'],  # Keep the formatted date as is for display
        reverse=True
    )
)

# Write JSON
TEMP_JSON.parent.mkdir(parents=True, exist_ok=True)
with open(TEMP_JSON, 'w', encoding='utf-8') as f:
    json.dump(output_data_sorted, f, indent=4)
