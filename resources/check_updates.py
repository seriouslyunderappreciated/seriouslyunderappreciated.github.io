import csv
import subprocess
import os
import requests
from datetime import datetime

BUILDS_FILE = "resources/builds.csv"
OUTPUT_FILE = "resources/temp.csv"

# -----------------------------------------------------
# Helper: fetch all builds with timestamps using DepotDownloader
# -----------------------------------------------------
def get_all_builds_with_timestamps(appid):
    """
    Returns a list of dicts: [{'buildid': int, 'timestamp': int}, ...]
    Timestamp is Unix epoch from the build manifest
    """
    result = subprocess.run(
        [
            "dotnet", "depotdownloader/DepotDownloader.dll",
            "-app", str(appid),
            "-username", os.environ["STEAM_USERNAME"],
            "-password", os.environ["STEAM_PASSWORD"],
            "-listdepots",
            "-v"  # verbose mode to get timestamps
        ],
        capture_output=True,
        text=True
    )

    builds = []
    current_build = {}
    for line in result.stdout.splitlines():
        line_lower = line.lower()
        if "buildid" in line_lower:
            try:
                current_build['buildid'] = int(line.split(":")[-1].strip())
            except ValueError:
                current_build = {}
        if "timecreated" in line_lower or "timestamp" in line_lower:
            try:
                current_build['timestamp'] = int(line.split(":")[-1].strip())
            except ValueError:
                continue
        # If we have both buildid and timestamp, append and reset
        if 'buildid' in current_build and 'timestamp' in current_build:
            builds.append(current_build)
            current_build = {}
    return builds

# -----------------------------------------------------
# Helper: fetch patch notes for appid
# -----------------------------------------------------
def get_patchnotes(appid):
    """
    Returns list of patch notes with title and timestamp
    """
    url = f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid={appid}&count=50"
    try:
        data = requests.get(url, timeout=10).json()
    except Exception as e:
        print(f"Failed to fetch news for appid {appid}: {e}")
        return []

    notes = []
    items = data.get("appnews", {}).get("newsitems", [])
    for item in items:
        title = item.get("title", "").strip()
        if title and title.lower() != "no title":
            notes.append({
                "title": title,
                "timestamp": item["date"]
            })
    return notes

# -----------------------------------------------------
# Main logic
# -----------------------------------------------------
output_rows = []

with open(BUILDS_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for row in reader:
        appid = row["appid"].strip()
        if not appid.isdigit():
            continue
        appid = int(appid)

        print(f"Processing appid {appid}...")

        builds = get_all_builds_with_timestamps(appid)
        if not builds:
            print(f"No builds found for appid {appid}")
            continue

        patch_notes = get_patchnotes(appid)
        if not patch_notes:
            print(f"No patch notes found for appid {appid}")
            continue

        # Find the latest build that has associated patch notes
        latest_build_with_notes = None
        latest_note_timestamp = 0

        for note in patch_notes:
            note_ts = note["timestamp"]
            # Find the newest build whose timestamp <= patch note timestamp
            candidate_builds = [b for b in builds if b["timestamp"] <= note_ts]
            if candidate_builds:
                # pick the build with largest timestamp
                build = max(candidate_builds, key=lambda b: b["timestamp"])
                if build["timestamp"] > latest_note_timestamp:
                    latest_note_timestamp = build["timestamp"]
                    latest_build_with_notes = build

        if latest_build_with_notes:
            patch_date = datetime.utcfromtimestamp(latest_build_with_notes["timestamp"]).strftime("%Y-%m-%d %H:%M:%S")
            output_rows.append({
                "appid": appid,
                "buildid": latest_build_with_notes["buildid"],
                "date": patch_date
            })
        else:
            print(f"No build matches patch notes for appid {appid}")

# Write output
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    fieldnames = ["appid", "buildid", "date"]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(output_rows)

print(f"Done. Wrote {len(output_rows)} entries to {OUTPUT_FILE}.")
