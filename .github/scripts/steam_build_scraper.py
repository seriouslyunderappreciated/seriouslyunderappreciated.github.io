import csv
import json
import requests
from datetime import datetime

def get_latest_public_buildid(appid: int) -> str | None:
    """
    Fetches the latest public branch build ID for a given Steam AppID
    using the unofficial public API endpoint.
    """
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return None

    try:
        return data['data'][str(appid)]['depots']['branches']['public']['buildid']
    except KeyError:
        return None

def get_latest_public_timeupdated(appid: int) -> str | None:
    """
    Fetches the latest public branch 'timeupdated' value and formats it
    the same way as in the current script.
    """
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        return None

    try:
        timestamp = int(data['data'][str(appid)]['depots']['branches']['public']['timeupdated'])
        return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
    except KeyError:
        return None

# Load builds.csv into a dictionary mapping appid -> buildid
builds_csv = {}
with open('resources/builds.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        builds_csv[row['appid']] = row['buildid']

# Example list of appids to check (use the keys from builds.csv)
app_ids = list(builds_csv.keys())

temp_data = {}

for appid in app_ids:
    latest_buildid = get_latest_public_buildid(int(appid))
    if latest_buildid is None:
        continue  # skip if no buildid found

    # Skip if the latest buildid matches the one in builds.csv
    if latest_buildid == builds_csv.get(appid):
        continue

    # Only add if buildid is new
    date = get_latest_public_timeupdated(int(appid)) or ''
    temp_data[appid] = {
        "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg",
        "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes",
        "date": date
    }

# Write the JSON
with open('resources/temp.json', 'w', encoding='utf-8') as f:
    json.dump(temp_data, f, indent=2)
