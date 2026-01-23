import csv
import json
import requests
import re
import time
from datetime import datetime
from pathlib import Path

def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + suffix

def make_keywords(game_name: str) -> str:
    words = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)*", game_name.lower())
    return "+".join(words)

def get_steam_app_metadata(appid: int):
    """
    Fetches build ID, timestamp, and the modern library capsule path in one call.
    """
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        app_info = data.get('data', {}).get(str(appid), {})
        if not app_info:
            return None

        # Extract Build ID and Timestamp
        branch_data = app_info.get('depots', {}).get('branches', {}).get('public', {})
        buildid = branch_data.get('buildid')
        timestamp = branch_data.get('timeupdated')

        # Extract Modern Library Capsule (the new cover logic)
        capsule_path = (
            app_info.get("common", {})
            .get("library_assets_full", {})
            .get("library_capsule", {})
            .get("image", {})
            .get("english")
        )

        return {
            "buildid": buildid,
            "timestamp": int(timestamp) if timestamp else None,
            "capsule_path": capsule_path
        }
    except Exception:
        return None

# Load builds.csv
builds_csv = {}
try:
    with open('data/builds.csv', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            builds_csv[row['appid']] = {
                "buildid": row['buildid'],
                "game": row['game']
            }
except FileNotFoundError:
    print("Error: data/builds.csv not found.")
    exit()

temp_data_with_ts = []

for appid in builds_csv.keys():
    print(f"Checking AppID: {appid}...")
    metadata = get_steam_app_metadata(int(appid))
    
    if not metadata or not metadata['buildid']:
        continue

    # Skip if build hasn't changed
    if str(metadata['buildid']) == builds_csv[appid]["buildid"]:
        continue

    # Format Date
    dt = datetime.utcfromtimestamp(metadata['timestamp'])
    formatted_date = dt.strftime(f"%B {ordinal(dt.day)}, %Y")

    # Construct Keywords and URLs
    game_name = builds_csv[appid]["game"]
    keywords = make_keywords(game_name)
    rinurl = f"https://cs.rin.ru/forum/search.php?st=0&sk=t&sd=d&sr=topics&keywords={keywords}&terms=all&fid[]=10&sf=titleonly"

    # CONSTRUCTION OF NEW COVER URL
    # Fallback to the old header if the modern library capsule isn't found
    if metadata['capsule_path']:
        cover_url = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/{metadata['capsule_path']}"
    else:
        cover_url = f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"

    temp_data_with_ts.append((
        metadata['timestamp'],
        appid,
        {
            "steamheader": cover_url,
            "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes",
            "date": formatted_date,
            "rinurl": rinurl
        }
    ))
    
    # Respect the API
    time.sleep(0.5)

# Sort newest → oldest
temp_data_with_ts.sort(reverse=True, key=lambda x: x[0])

# Build final dictionary
temp_data = {appid: data for _, appid, data in temp_data_with_ts}

# Write output JSON
output_path = Path('data/temp.json')
output_path.parent.mkdir(exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(temp_data, f, indent=2)

print(f"Done! Updated {len(temp_data)} entries.")
