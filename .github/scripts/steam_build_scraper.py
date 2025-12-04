import os
import requests
import pandas as pd
from datetime import datetime
from steam.client import SteamClient

# --- CONFIG ---
STEAM_USER = os.environ["STEAM_USERNAME"]
STEAM_PASS = os.environ["STEAM_PASSWORD"]
CSV_SOURCE = "resources/builds.csv"
CSV_OUT = "resources/temp.csv"

# --- KEYWORDS that imply patch notes rather than fluff ---
PATCH_KEYWORDS = [
    "patch", "fix", "hotfix", "update", "notes", "balancing",
    "changelog", "bug", "version", "improved", "resolved",
]

# --- LOGIN TO STEAM ---
client = SteamClient()
client.login(STEAM_USER, STEAM_PASS)

# --- READ APPIDS ---
df = pd.read_csv(CSV_SOURCE)
appids = df["appid"].dropna().astype(int).unique()

results = []

for appid in appids:
    print(f"Checking {appid}")

    # --- GET BUILDS VIA STEAM API ---
    try:
        r = requests.get(
            f"https://api.steampowered.com/ISteamApps/GetAppBuilds/v1/",
            params={"appid": appid}
        )
        builds = r.json().get("response", {}).get("builds", [])
    except:
        builds = []

    if not builds:
        continue

    # Convert build list into DataFrame and normalize date
    bdf = pd.DataFrame(builds)
    if "date" not in bdf:
        continue

    bdf["date"] = pd.to_datetime(bdf["date"], unit="s").dt.date

    # --- FETCH STEAM ANNOUNCEMENTS ---
    ann = requests.get(
        f"https://steamcommunity.com/games/{appid}/announcements/"
    ).text.lower()

    # Extract announcement links from the HTML
    links = [
        l.split('"')[0] for l in ann.split('href="')
        if "announcements/detail" in l
    ]

    # --- Find announcements that look like patch notes ---
    valid_announcements = []
    for link in links:
        try:
            text = requests.get(link).text.lower()
            date_line = text.split("date posted: ")[-1][:10]  # approximate extract
            post_date = datetime.strptime(date_line, "%Y-%m-%d").date()

            if any(k in text for k in PATCH_KEYWORDS):
                valid_announcements.append((post_date, link))
        except:
            pass

    if not valid_announcements:
        continue

    # Convert to DF
    adf = pd.DataFrame(valid_announcements, columns=["post_date", "link"])

    # --- Find builds released on same day as patch notes ---
    merged = bdf.merge(
        adf, left_on="date", right_on="post_date"
    )

    if merged.empty:
        continue

    # Pick most recent matching build
    merged = merged.sort_values("buildid", ascending=False)
    best = merged.iloc[0]

    results.append({
        "appid": appid,
        "buildid": int(best["buildid"]),
        "date": best["date"].isoformat(),
    })

# --- WRITE OUTPUT ---
out = pd.DataFrame(results)
out.to_csv(CSV_OUT, index=False)
print("Wrote temp.csv")

client.logout()
