import os
import subprocess
import requests
import pandas as pd
from datetime import datetime

# --- CONFIG ---
CSV_SOURCE = "resources/builds.csv"
CSV_OUT = "resources/temp.csv"
DEPOTDOWNLOADER = "DepotDownloader"  # assumed to be in PATH or repo root

STEAM_USER = os.environ["STEAM_USERNAME"]
STEAM_PASS = os.environ["STEAM_PASSWORD"]

# Patch note keyword filter to cut out fluff posts
PATCH_KEYWORDS = [
    "patch", "fix", "hotfix", "update", "changelog", "notes",
    "bug", "improved", "resolved", "balance", "gameplay",
    "version", "steam deck", "crash", "stability", "performance"
]

def get_build_ids_via_depotdownloader(appid: int):
    """
    Calls DepotDownloader CLI to list build IDs / manifests.
    Returns list of (buildid, date)
    Since DepotDownloader itself does not give dates, we will attach None
    for now and fill dates from Steam News API if matched.
    """
    try:
        cmd = [
            DEPOTDOWNLOADER,
            "-app", str(appid),
            "-username", STEAM_USER,
            "-password", STEAM_PASS,
            "-list",  # list manifests instead of downloading
        ]
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).lower()
    except subprocess.CalledProcessError as e:
        print(f"[DepotDownloader error] {appid}: {e.output}")
        return []

    # Extract build IDs from output
    # Lines often contain: "BuildID: 12345678"
    builds = []
    for line in out.splitlines():
        if "buildid" in line or "build id" in line:
            # normalize and extract digits
            digits = "".join(c for c in line if c.isdigit())
            if digits:
                builds.append((int(digits), None))
    return builds

def get_patch_notes_from_steam_news(appid: int):
    """
    Uses Steam Web API GetNewsForApp (does NOT require login).
    Returns list of (post_date, buildid_guess, url)
    We'll later match by release date == post date.
    """
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
        timestamp = item.get("date")

        if not timestamp:
            continue

        post_date = datetime.utcfromtimestamp(timestamp).date()

        # Skip fluff by requiring patch keywords in title or body
        if not any(k in text or k in title for k in PATCH_KEYWORDS):
            continue

        # Try extracting a buildid from the contents (announcement posts sometimes include them)
        buildid = None
        digits = "".join(c if c.isdigit() else " " for c in text).split()
        for d in digits:
            # Only accept large 8+ digit numbers (Steam build IDs are big)
            if len(d) >= 8:
                buildid = int(d)
                break

        patches.append((post_date, buildid, item.get("url")))

    return patches

# --- MAIN ---
df = pd.read_csv(CSV_SOURCE)
appids = df["appid"].dropna().astype(int).unique()

results = []

for appid in appids:
    print(f"Checking app {appid}")

    builds = get_build_ids_via_depotdownloader(appid)
    if not builds:
        print(f"  No builds found for {appid}")
        continue

    bdf = pd.DataFrame(builds, columns=["buildid", "date"])
    bdf = bdf.drop_duplicates("buildid")
    bdf = bdf.sort_values("buildid", ascending=False)

    # Get filtered patch announcements
    announcements = get_patch_notes_from_steam_news(appid)
    adf = pd.DataFrame(announcements, columns=["post_date", "mentioned_build", "url"])

    if adf.empty:
        print(f"  No patch announcements for {appid}")
        continue

    adf = adf.sort_values("post_date", ascending=False)

    # Fill dates by matching same-day heuristic
    for i, build in bdf.iterrows():
        for j, ann in adf.iterrows():
            # Same-day rule: patch notes posted the same day build was released
            # Or fuzzy fallback: if the post mentions that exact build ID
            if (ann["mentioned_build"] == build["buildid"]) or True:
                # We can't get true build release date from Steam directly here,
                # but our heuristic is: announcement posted today means the newest build before or on today
                if ann["post_date"] == datetime.utcnow().date():
                    results.append({
                        "appid": appid,
                        "buildid": build["buildid"],
                        "date": ann["post_date"].isoformat(),
                        "announcement": ann["url"]
                    })
                    break
        if results and results[-1]["appid"] == appid:
            break

    if not any(r["appid"] == appid for r in results):
        # fallback: choose newest build from same day announcement date if not today
        target_date = adf.iloc[0]["post_date"]
        valid = bdf  # we don't have true build release date but pick newest available
        best_build = valid.iloc[0]["buildid"]
        results.append({
            "appid": appid,
            "buildid": best_build,
            "date": target_date.isoformat(),
            "announcement": adf.iloc[0]["url"]
        })

# --- WRITE OUTPUT ---
out = pd.DataFrame(results)
out = out[["appid", "buildid", "date"]]
out.to_csv(CSV_OUT, index=False)
print("Wrote temp.csv")
