import os
import requests
import time
import json

# -----------------------------
# Configuration
# -----------------------------
PLATFORMS = [6, 130, 438]        # PC, Switch, Switch 2
EXCLUDE_THEMES = [19, 42]        # Horror, Erotica
EXCLUDE_GENRES = [14, 26, 13]    # Sport, Quiz, Simulator

OUTPUT_PATH = "data/igdb.json"


def fetch_igdb_data():
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Missing IGDB_CLIENT_ID or IGDB_CLIENT_SECRET")

    # -----------------------------
    # 1. Authenticate
    # -----------------------------
    auth_url = (
        "https://id.twitch.tv/oauth2/token"
        f"?client_id={client_id}"
        f"&client_secret={client_secret}"
        "&grant_type=client_credentials"
    )

    auth_res = requests.post(auth_url, timeout=10)
    auth_res.raise_for_status()
    token = auth_res.json()["access_token"]

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    # -----------------------------
    # 2. Time Window
    # -----------------------------
    now = int(time.time())
    thirty_days_ago = now - (30 * 86400)

    p_str = ",".join(map(str, PLATFORMS))
    t_str = ",".join(map(str, EXCLUDE_THEMES))
    g_str = ",".join(map(str, EXCLUDE_GENRES))

    BASE_WHERE = (
        f"first_release_date > {thirty_days_ago} "
        f"& first_release_date <= {now} "
        f"& platforms = ({p_str}) "
        f"& themes != ({t_str}) "
        f"& genres != ({g_str}) "
        f"& category = (0, 8, 9) "
    )

    QUALITY_LEVELS = [
        # Strict
        "& (follows > 15 | rating_count > 20 | aggregated_rating_count > 5) "
        "& cover != null "
        "& game_modes = (1) ",

        # Good
        "& (follows > 8 | rating_count > 10) ",

        # Acceptable
        "& follows > 3 ",

        # Fallback
        ""
    ]

    games = []

    # -----------------------------
    # 3. Query with Relaxation
    # -----------------------------
    for level, quality_filter in enumerate(QUALITY_LEVELS, start=1):
        query = (
            "fields name, first_release_date, platforms.id, platforms.name, "
            "cover.url, websites.url, websites.category, "
            "follows, rating, rating_count, aggregated_rating; "
            "where "
            + BASE_WHERE
            + quality_filter +
            "sort first_release_date desc; "
            "limit 50;"
        )

        response = requests.post(
            "https://api.igdb.com/v4/games",
            headers=headers,
            data=query,
            timeout=15,
        )

        if response.status_code != 200:
            print("IGDB QUERY ERROR:")
            print(response.text)
            response.raise_for_status()

        games = response.json()
        if games:
            print(f"Quality level {level} matched {len(games)} games.")
            break

    if not games:
        print("No games found after all relaxations.")
        return

    processed = []

    # -----------------------------
    # 4. Normalize Output
    # -----------------------------
    for g in games:
        platform_ids = [p.get("id") for p in g.get("platforms", [])]

        if 6 in platform_ids:
            platform_name = "PC"
        elif 438 in platform_ids:
            platform_name = "Nintendo Switch 2"
        elif 130 in platform_ids:
            platform_name = "Nintendo Switch"
        else:
            continue

        cover = None
        if g.get("cover") and g["cover"].get("url"):
            cover = "https:" + g["cover"]["url"].replace(
                "t_thumb", "t_cover_big"
            )

        steam_url = None
        for w in g.get("websites", []):
            if w.get("category") == 13:
                steam_url = w.get("url")
                break

        processed.append({
            "name": g.get("name"),
            "date": g.get("first_release_date"),
            "platform": platform_name,
            "cover": cover,
            "url": steam_url,
            "follows": g.get("follows"),
            "rating": g.get("rating"),
            "rating_count": g.get("rating_count"),
            "aggregated_rating": g.get("aggregated_rating"),
        })

    # -----------------------------
    # 5. Save
    # -----------------------------
    os.makedirs("data", exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"Successfully processed {len(processed)} games.")


if __name__ == "__main__":
    fetch_igdb_data()
