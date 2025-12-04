import json
import subprocess
import requests
import os
from datetime import datetime, timezone

# -----------------------------------------------------
# CONFIG: Add the Steam app IDs you track here
# -----------------------------------------------------
APPIDS = [
    1086940,  # Baldur's Gate 3 example
    # Add more appIDs here
]

OUTPUT_FILE = "resources/updates.json"

# -----------------------------------------------------
# Helper: get latest buildID using DepotDownloader
# -----------------------------------------------------
def get_buildid(appid):
    result = subprocess.run(
        [
            "dotnet", "depotdownloader/DepotDownloader.dll",
            "-app", str(appid),
            "-username", os.environ["STEAM_USERNAME"],
            "-password", os.environ["STEAM_PASSWORD"],
            "-listdepots"
        ],
        capture_output=True,
        text=True
    )

    # Parse buildID from output
    for line in result.stdout.splitlines():
        if "buildid" in line.lower():
            return int(line.split(":")[-1].strip())

    return None


# -----------------------------------------------------
# Helper: get latest patch note title + timestamp
# -----------------------------------------------------
def get_latest_patchnote(appid):
    url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={appid}&count=5"
    data = requests.get(url).json()
    items = data.get("appnews", {}).get("newsitems", [])

    for item in items:
        title = item.get("title", "").strip()

        # Ignore non-titled updates ("No title" silent builds)
        if title and title.lower() != "no title":
            return {
                "title": title,
                "timestamp": item["date"]
            }

    return None


# -----------------------------------------------------
# Main logic: compare buildID vs patch note time
# -----------------------------------------------------
updates = {}

for appid in APPIDS:
    buildid = get_buildid(appid)
    note = get_latest_patchnote(appid)

    has_patch_build = False

    if buildid and note:
        # If patch note timestamp is within the last ~2 days, treat as new
        now = datetime.now(timezone.utc).timestamp()
        if now - note["timestamp"] < 172800:  # 48 hours
            has_patch_build = True

    updates[str(appid)] = {
        "latestBuild": buildid,
        "patchNoteTitle": note["title"] if note else None,
        "patchNoteTime": note["timestamp"] if note else None,
        "hasPatchBuild": has_patch_build
    }

# -----------------------------------------------------
# Save JSON output
# -----------------------------------------------------
with open(OUTPUT_FILE, "w") as f:
    json.dump(updates, f, indent=4)

print("Updated:", OUTPUT_FILE)
