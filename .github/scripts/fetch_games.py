import os
import json
import re
import requests
from datetime import datetime, timedelta, UTC
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# ---------------------- CONFIG ------------------------------
# ============================================================

DAYS_BACK = 30

TOP_N_HYPES = 20   # shortlist after IGDB hypes
TOP_FINAL = 6      # final list after Steam reviews

PC_PLATFORM_ID = 6
SINGLE_PLAYER_MODE_ID = 1

EXCLUDED_GENRES = {13, 14, 26}   # Simulator, Sport, Quiz/Trivia
EXCLUDED_THEMES = {19}           # Horror

STEAM_EXTERNAL_SOURCE = 1
STEAM_WEBSITE_TYPE = 13          # Modern way to filter websites for Steam

STEAM_REVIEW_URL = (
    "https://store.steampowered.com/appreviews/"
    "{appid}?json=1&language=all&num_per_page=0"
)

STEAM_APPID_REGEX = re.compile(r"/app/(\d+)")

# ============================================================
# ------------------- IGDB HELPERS ----------------------------
# ============================================================

def get_access_token(client_id, client_secret):
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
    }
    r = requests.post(url, params=params)
    r.raise_for_status()
    return r.json()["access_token"]

def igdb_request(endpoint, query, access_token, client_id):
    url = f"https://api.igdb.com/v4/{endpoint}"
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    r = requests.post(url, headers=headers, data=query)
    r.raise_for_status()
    return r.json()

# ============================================================
# -------------------- FETCH DATA -----------------------------
# ============================================================

def fetch_games(access_token, client_id):
    now_utc = datetime.now(UTC)
    start_ts = int((now_utc - timedelta(days=DAYS_BACK)).timestamp())
    end_ts = int(now_utc.timestamp())

    query = f"""
    fields id, name, platforms, game_modes, genres, themes, cover, hypes;
    where
      first_release_date >= {start_ts}
      & first_release_date <= {end_ts}
      & game_type = 0;
    limit 500;
    """
    return igdb_request("games", query, access_token, client_id)

def fetch_steam_appids_external(game_ids, access_token, client_id):
    if not game_ids:
        return {}
    ids = ",".join(map(str, game_ids))
    query = f"""
    fields game, uid;
    where game = ({ids}) & external_game_source = {STEAM_EXTERNAL_SOURCE};
    """
    results = igdb_request("external_games", query, access_token, client_id)
    return {row["game"]: row["uid"] for row in results}

def fetch_steam_appids_websites(game_ids, access_token, client_id):
    if not game_ids:
        return {}
    ids = ",".join(map(str, game_ids))
    query = f"""
    fields game, url;
    where game = ({ids}) & type = {STEAM_WEBSITE_TYPE};
    """
    results = igdb_request("websites", query, access_token, client_id)

    steam_ids = {}
    for row in results:
        match = STEAM_APPID_REGEX.search(row.get("url", ""))
        if match:
            steam_ids[row["game"]] = match.group(1)
    return steam_ids

def fetch_platforms(platform_ids, access_token, client_id):
    if not platform_ids:
        return {}
    ids = ",".join(map(str, platform_ids))
    query = f"fields id, name; where id = ({ids});"
    results = igdb_request("platforms", query, access_token, client_id)
    return {p["id"]: p["name"] for p in results}

def fetch_covers(cover_ids, access_token, client_id):
    if not cover_ids:
        return {}
    ids = ",".join(map(str, cover_ids))
    query = f"fields id, image_id; where id = ({ids});"
    results = igdb_request("covers", query, access_token, client_id)
    return {c["id"]: c["image_id"] for c in results}

def fetch_genres(access_token, client_id):
    results = igdb_request("genres", "fields id, name; limit 500;", access_token, client_id)
    return {g["id"]: g["name"] for g in results}

def fetch_themes(access_token, client_id):
    results = igdb_request("themes", "fields id, name; limit 500;", access_token, client_id)
    return {t["id"]: t["name"] for t in results}

# ============================================================
# -------------------- FILTERING ------------------------------
# ============================================================

def is_allowed_game(game):
    platforms = set(game.get("platforms", []))
    modes = set(game.get("game_modes", []))
    genres = set(game.get("genres", []))
    themes = set(game.get("themes", []))

    if PC_PLATFORM_ID not in platforms:
        return False
    if SINGLE_PLAYER_MODE_ID not in modes:
        return False
    if genres & EXCLUDED_GENRES:
        return False
    if themes & EXCLUDED_THEMES:
        return False

    return True

# ============================================================
# ------------------ STEAM REVIEWS ----------------------------
# ============================================================

def fetch_steam_total_positive(appid):
    try:
        r = requests.get(STEAM_REVIEW_URL.format(appid=appid), timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("query_summary", {}).get("total_positive", 0)
    except Exception:
        return 0

# ============================================================
# ---------------------- MAIN --------------------------------
# ============================================================

def main():
    client_id = os.getenv("IGDB_CLIENT_ID")
    client_secret = os.getenv("IGDB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing IGDB credentials")

    access_token = get_access_token(client_id, client_secret)

    print("Fetching IGDB games...")
    games = fetch_games(access_token, client_id)

    print("Applying filters...")
    games = [g for g in games if is_allowed_game(g)]
    print(f"After filtering: {len(games)} games")

    game_ids = [g["id"] for g in games]

    print("Resolving Steam AppIDs...")
    steam_external = fetch_steam_appids_external(game_ids, access_token, client_id)
    steam_websites = fetch_steam_appids_websites(game_ids, access_token, client_id)
    print(
        f"Steam IDs found: {len(steam_external)} via external_games, "
        f"{len(steam_websites)} via websites"
    )

    for g in games:
        g["steam_appid"] = steam_external.get(g["id"]) or steam_websites.get(g["id"])

    games = [g for g in games if g.get("steam_appid")]
    print(f"Steam games remaining: {len(games)}")

    games.sort(key=lambda g: g.get("hypes", 0), reverse=True)
    games = games[:TOP_N_HYPES]

    print("Fetching Steam review counts (parallel)...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch_steam_total_positive, g["steam_appid"]): g
            for g in games
        }
        for future in as_completed(futures):
            game = futures[future]
            game["total_positive"] = future.result()

    games.sort(key=lambda g: g.get("total_positive", 0), reverse=True)
    games = games[:TOP_FINAL]

    # Metadata
    platform_ids = {pid for g in games for pid in g.get("platforms", [])}
    cover_ids = [g["cover"] for g in games if "cover" in g]

    platforms_map = fetch_platforms(platform_ids, access_token, client_id)
    covers_map = fetch_covers(cover_ids, access_token, client_id)
    genres_map = fetch_genres(access_token, client_id)
    themes_map = fetch_themes(access_token, client_id)

    output = []
    for g in games:
        entry = {
            "name": g["name"],
            "steam_appid": g["steam_appid"],
            "total_positive": g.get("total_positive", 0),
            "platforms": [platforms_map.get(pid) for pid in g.get("platforms", [])],
            "genres": [{"id": gid, "name": genres_map.get(gid)} for gid in g.get("genres", [])],
            "themes": [{"id": tid, "name": themes_map.get(tid)} for tid in g.get("themes", [])],
            "cover_url": None,
        }
        cover_id = g.get("cover")
        if cover_id in covers_map:
            entry["cover_url"] = (
                f"https://images.igdb.com/igdb/image/upload/t_cover_big/{covers_map[cover_id]}.jpg"
            )
        output.append(entry)

    os.makedirs("data", exist_ok=True)
    with open("data/igdb.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(output)} games to data/igdb.json")

if __name__ == "__main__":
    main()
