import os
import subprocess
import requests
import pandas as pd
from datetime import datetime

# --- CONFIG ---
CSV_SOURCE = "resources/builds.csv"
CSV_OUT = "resources/temp.csv"
DEPOTDOWNLOADER = "DepotDownloader"  # binary installed by workflow

STEAM_USER = os.environ["STEAM_USERNAME"]
STEAM_PASS = os.environ["STEAM_PASSWORD"]

PATCH_KEYWORDS = [
    "patch", "fix", "hotfix", "update", "changelog", "notes",
    "bug", "improved", "resolved", "balance", "gameplay",
    "version", "steam deck", "crash", "stability", "performance"
]

def get_build_ids_via_depotdownloader(appid: int):
    try:
        cmd = [
            "./" + DEPOTDOWNLOADER,
            "-app", str(appid),
            "-username", STEAM_USER,
            "-password", STEAM_PASS,
            "-list"
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).lower()
    except subprocess.CalledProcessError as e:
        print(f"[DepotDownloader error] {appid}: {e.output}")
        return []

    builds = []
    for line in out.splitlines():
        if "buildid" in line or "build id" in line:
            digits = "".join(c for c in line if c.isdigit())
            if digits:
                builds.append((int(digits), None))
    return builds

def get_patch_notes_from_steam_news(appid: int):
    try:
        r = requests.get(
            "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/",
            params={"appid": appid, "count": 50}
        )
        items = r.json().get("appnews", {}).get("newsitems", [])
    except Exception as e:
        print(f"[Steam News error] {appid}: {e}")
        return []

    patches = []
    for item in items:
        text = (item.get("contents") or "").lower()
        title = (item.get("title") or "").lower()
        ts = item.get("date")
        if not ts:
            continue

        post_date = datetime.utcfromtimestamp(ts).date()

        if not any(k in text or k in title for k in PATCH_KEYWORDS):
            continue

        buildid = None
        nums = "".join(c if c.isdigit() else " " for c in text).split()
        for n in nums:
            if len(n) >= 8:
                buildid = int(n)
                break

        patches.append((post_date, buildid, item.get("url")))

    return patches

# --- MAIN EXECUTION ---
df = pd.read_csv(CSV_SOURCE)
appids = df["appid"].dropna().astype(int).unique()

results = []

for appid in appids:
    print(f"Checking app {appid}")

    builds = get_build_ids_via_depotdownloader(appid)
    if not builds:
        print("  No builds found")
        continue

    bdf = pd.DataFrame(builds, columns=["buildid", "date"])
    bdf = bdf.drop_duplicates("buildid")
    bdf = bdf.sort_values("buildid", ascending=False)

    announcements = get_patch_notes_from_steam_news(appid)
    adf = pd.DataFrame(announcements, columns=["post_date", "mentioned_build", "url"])
    if adf.empty:
        print("  No patch-note style announcements")
        continue

    adf = adf.sort_values("post_date", ascending=False)
    target_date = adf.iloc[0]["post_date"]

    chosen = None

    for _, build in bdf.iterrows():
        for _, ann in adf.iterrows():
            # ✅ Correct match logic
            if ann["mentioned_build"] == build["buildid"]:
                chosen = (build["buildid"], ann["post_date"], ann["url"])
                break
            elif ann["post_date"] == target_date:
                chosen = (build["buildid"], ann["post_date"], ann["url"])
                break
        if chosen:
            break

    if not chosen:
        # ✅ Only fall back if no valid match found
        fallback_build = bdf.iloc[0]["buildid"]
        chosen = (fallback_build, target_date, adf.iloc[0]["url"])
        print(f"  Falling back to newest build: {fallback_build}")

    buildid, date, url = chosen
    print(f"  Selected Build: {buildid} ({date})")

    results.append({
        "appid": appid,
        "buildid": int(buildid),
        "date": date.isoformat(),
        "announcement": url
    })

# ✅ Write only the columns you care about
out = pd.DataFrame(results)
out = out[["appid", "buildid", "date"]]
out.to_csv(CSV_OUT, index=False)
print("Wrote temp.csv")
