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
    # 1. Authenticate with Twitch
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
    # 2. Time Window (last 30 days)
    # -----------------------------
    now = int(time.time())
    thirty_days_ago = now - (30 * 86400)

    p_str = ",".join(map(str, PLATFORMS))
    t_str = ",".join(map(str, EXCLUDE_THEMES))
    g_str = ",".join(map(str, EXCLUDE_GENRES))

    # -----------------------------
    # 3. IGDB Query
    # -----------------------------
    query = (
        "fields "
        "name, "
        "first_release_date, "
        "platforms.id, platforms.name, "
        "cover.url, "
        "websites.url, websites.category, "
        "follows, rating, rating_count, "
        "aggregated_rating, aggregated_rating_count; "

        f"where first_release_date > {thirty_days_ago} "
        f"& first_release_date <= {now} "
        f"& platforms = ({p_str}) "
        f"& game_modes = (1) "
        f"& (follows > 15 | rating_count > 20 | aggregated_rating_count > 5) "
        f"& themes != ({t_str}) "
        f"& genres != ({g_str}) "
        f"& category = (0, 8, 9) "
        f"& cover != null; "

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
    processed = []

    # -----------------------------
    # 4. Normalize Results
    # -----------------------------
    for g in games:
        platforms = g.get("platforms", [])
        platform_ids = [p.get("id") for p in platforms]

        # Platform priority
        if 6 in platform_ids:
            platform_name = "PC"
        elif 438 in platform_ids:
            platform_name = "Nintendo Switch 2"
        elif 130 in platform_ids:
            platform_name = "Nintendo Switch"
        else:
            continue  # Should never happen, but safe

        # Cover image
        cover = None
        if "cover" in g and "url" in g["cover"]:
            cover = "https:" + g["cover"]["url"].replace(
                "t_thumb", "t_cover_big"
            )

        # Steam link (website category 13)
        steam_url = None
        for w in g.get("websites", []):
            if w.get("category") == 13:
                steam_url = w.get("url")
                break

        processed.append(
            {
                "name": g.get("name"),
                "date": g.get("first_release_date"),
                "platform": platform_name,
                "cover": cover,
                "url": steam_url,
                "follows": g.get("follows"),
                "rating": g.get("rating"),
                "rating_count": g.get("rating_count"),
                "aggregated_rating": g.get("aggregated_rating"),
            }
        )

    # -----------------------------
    # 5. Save Output
    # -----------------------------
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(processed, f, indent=2, ensure_ascii=False)

    print(f"Successfully processed {len(processed)} games.")


if __name__ == "__main__":
    fetch_igdb_data()
