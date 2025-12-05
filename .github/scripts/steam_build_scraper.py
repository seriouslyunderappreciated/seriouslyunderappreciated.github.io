import csv
import json
import requests
import re
from datetime import datetime

def ordinal(n: int) -> str:
    """Return ordinal string for a number, e.g., 1 -> 1st, 2 -> 2nd"""
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return str(n) + suffix


def make_keywords(game_name: str) -> str:
    """
    Convert a game title into a search keyword string:
    - lowercase
    - keep letters, numbers, and apostrophes inside words
    - allow multiple apostrophes in a word
    - remove all other punctuation
    - join with '+'
    """
    # Matches words consisting of letters/numbers with apostrophes anywhere except leading/trailing
    # Examples: clancy's, o'neill, king's, rock'n'roll
    words = re.findall(r"[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)*", game_name.lower())
    return "+".join(words)


def get_latest_public_buildid(appid: int) -> str | None:
    """Fetch the latest public build ID for a Steam AppID."""
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


def get_latest_public_timeupdated(appid: int) -> tuple[int, str] | None:
    """
    Fetch the latest public 'timeupdated' for a Steam AppID.
    Returns a tuple: (timestamp, formatted date string)
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
        dt = datetime.utcfromtimestamp(timestamp)
        formatted_date = dt.strftime(f"%B {ordinal(dt.day)}, %Y")
        return timestamp, formatted_date
    except KeyError:
        return None


# Load builds.csv → dict: appid -> {buildid, game}
builds_csv = {}
with open('resources/builds.csv', newline='', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        builds_csv[row['appid']] = {
            "buildid": row['buildid'],
            "game": row['game']
        }

# List of appids
app_ids = list(builds_csv.keys())

temp_data = {}
temp_data_with_ts = []

for appid in app_ids:
    latest_buildid = get_latest_public_buildid(int(appid))
    if latest_buildid is None:
        continue

    # Skip unchanged build
    if latest_buildid == builds_csv[appid]["buildid"]:
        continue

    timeupdated = get_latest_public_timeupdated(int(appid))
    if timeupdated is None:
        continue

    timestamp, formatted_date = timeupdated

    # Create keywords from cleaned game name
    game_name = builds_csv[appid]["game"]
    keywords = make_keywords(game_name)

    # Construct rinurl
    rinurl = (
        "https://example.com/forum/search.php?"
        f"st=0&sk=t&sd=d&sr=topics&keywords={keywords}"
        "&terms=all&fid[]=10&sf=titleonly"
    )

    temp_data_with_ts.append((
        timestamp,
        appid,
        {
            "steamheader": f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg",
            "steamdburl": f"https://steamdb.info/app/{appid}/patchnotes",
            "date": formatted_date,
            "rinurl": rinurl
        }
    ))

# Sort newest → oldest
temp_data_with_ts.sort(reverse=True, key=lambda x: x[0])

# Build final dictionary
temp_data = {appid: data for _, appid, data in temp_data_with_ts}

# Write output JSON
with open('resources/temp.json', 'w', encoding='utf-8') as f:
    json.dump(temp_data, f, indent=2)
