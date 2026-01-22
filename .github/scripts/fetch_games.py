import os
import json
import requests
import time
from datetime import datetime, timedelta, UTC
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# ---------------------- CONFIG ------------------------------
# ============================================================

DAYS_BACK = 30

PC_PLATFORM_ID = 6
SINGLE_PLAYER_MODE_ID = 1

EXCLUDED_GENRES = {13, 14, 26}   # Simulator, Sport, Quiz/Trivia
EXCLUDED_THEMES = {19}           # Horror

STEAM_EXTERNAL_SOURCE = 1

STEAM_REVIEW_URL = (
    "https://store.steampowered.com/appreviews/"
    "{appid}?json=1&language=all&num_per_page=0"
)

# IGDB rate limiting: 4 requests per second
IGDB_RATE_LIMIT = 4
IGDB_RATE_WINDOW = 1.0  # seconds

# ============================================================
# ------------------- RATE LIMITER ----------------------------
# ============================================================

class RateLimiter:
    def __init__(self, max_calls, time_window):
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = []
    
    def wait_if_needed(self):
        now = time.time()
        # Remove calls outside the time window
        self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        if len(self.calls) >= self.max_calls:
            # Need to wait
            oldest_call = self.calls[0]
            wait_time = self.time_window - (now - oldest_call)
            if wait_time > 0:
                time.sleep(wait_time)
            # Clean up again after waiting
            now = time.time()
            self.calls = [call_time for call_time in self.calls if now - call_time < self.time_window]
        
        self.calls.append(time.time())

# Global rate limiter for IGDB
igdb_limiter = RateLimiter(IGDB_RATE_LIMIT, IGDB_RATE_WINDOW)

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
    igdb_limiter.wait_if_needed()
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
# -------------------- STEP 1: FETCH GAMES -------------------
# ============================================================

def fetch_recent_games(access_token, client_id):
    """Fetch all games released in the last DAYS_BACK days"""
    now_utc = datetime.now(UTC)
    start_ts = int((now_utc - timedelta(days=DAYS_BACK)).timestamp())
    end_ts = int(now_utc.timestamp())

    query = f"""
    fields id, name, platforms, game_modes, genres, themes, cover;
    where
      first_release_date >= {start_ts}
      & first_release_date <= {end_ts}
      & game_type = 0;
    limit 500;
    """
    return igdb_request("games", query, access_token, client_id)

# ============================================================
# ---------- STEP 2 & 3: FILTERING ----------------------------
# ============================================================

def filter_games(games):
    """Filter for PC, single-player, and exclude unwanted genres/themes"""
    filtered = []
    
    for game in games:
        platforms = set(game.get("platforms", []))
        modes = set(game.get("game_modes", []))
        genres = set(game.get("genres", []))
        themes = set(game.get("themes", []))
        
        # Must have PC platform
        if PC_PLATFORM_ID not in platforms:
            continue
        
        # Must have single player mode
        if SINGLE_PLAYER_MODE_ID not in modes:
            continue
        
        # Exclude unwanted genres
        if genres & EXCLUDED_GENRES:
            continue
        
        # Exclude unwanted themes
        if themes & EXCLUDED_THEMES:
            continue
        
        filtered.append(game)
    
    return filtered

# ============================================================
# ---------- STEP 4: FETCH STEAM APP IDS ---------------------
# ============================================================

def fetch_steam_appids(game_ids, access_token, client_id):
    """Fetch Steam AppIDs from external_games endpoint"""
    if not game_ids:
        return {}
    
    ids = ",".join(map(str, game_ids))
    query = f"""
    fields game, uid;
    where game = ({ids}) & external_game_source = {STEAM_EXTERNAL_SOURCE};
    """
    results = igdb_request("external_games", query, access_token, client_id)
    return {row["game"]: row["uid"] for row in results}

# ============================================================
# ---------- STEP 6: FETCH STEAM REVIEWS ---------------------
# ============================================================

def fetch_steam_total_positive(appid):
    """Fetch total_positive reviews from Steam"""
    try:
        r = requests.get(STEAM_REVIEW_URL.format(appid=appid), timeout=10)
        r.raise_for_status()
        data = r.json()
        return data.get("query_summary", {}).get("total_positive", 0)
    except Exception:
        return 0

# ============================================================
# ---------- FETCH METADATA ----------------------------------
# ============================================================

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
# ---------------------- MAIN --------------------------------
# ============================================================

def main():
    client_id = os.getenv("IGDB_CLIENT_ID")
    client_secret = os.getenv("IGDB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RuntimeError("Missing IGDB credentials")

    access_token = get_access_token(client_id, client_secret)

    # STEP 1: Fetch all recent games
    print("Step 1: Fetching games from last 30 days...")
    games = fetch_recent_games(access_token, client_id)
    print(f"Found {len(games)} games")

    # STEP 2 & 3: Filter games
    print("Step 2-3: Filtering for PC, single-player, excluding genres/themes...")
    games = filter_games(games)
    print(f"After filtering: {len(games)} games")

    # STEP 4: Fetch Steam AppIDs
    print("Step 4: Fetching Steam AppIDs...")
    game_ids = [g["id"] for g in games]
    steam_appids = fetch_steam_appids(game_ids, access_token, client_id)
    print(f"Found Steam IDs for {len(steam_appids)} games")

    # STEP 5: Separate games with and without Steam IDs
    games_with_steam = []
    games_without_steam = []
    
    for game in games:
        steam_appid = steam_appids.get(game["id"])
        if steam_appid:
            game["steam_appid"] = steam_appid
            games_with_steam.append(game)
        else:
            games_without_steam.append(game)
    
    print(f"Games with Steam: {len(games_with_steam)}")
    print(f"Games without Steam: {len(games_without_steam)}")

    # STEP 6: Fetch Steam review counts
    print("Step 6: Fetching Steam review counts...")
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(fetch_steam_total_positive, g["steam_appid"]): g
            for g in games_with_steam
        }
        for future in as_completed(futures):
            game = futures[future]
            game["total_positive"] = future.result()

    # Sort by total_positive reviews
    games_with_steam.sort(key=lambda g: g.get("total_positive", 0), reverse=True)

    # Fetch metadata for all games
    print("Fetching metadata...")
    all_games = games_with_steam + games_without_steam
    platform_ids = {pid for g in all_games for pid in g.get("platforms", [])}
    cover_ids = [g["cover"] for g in all_games if "cover" in g]

    platforms_map = fetch_platforms(platform_ids, access_token, client_id)
    covers_map = fetch_covers(cover_ids, access_token, client_id)
    genres_map = fetch_genres(access_token, client_id)
    themes_map = fetch_themes(access_token, client_id)

    # Build output for games with Steam
    steam_games_output = []
    for g in games_with_steam:
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
        steam_games_output.append(entry)

    # Build output for games without Steam
    no_steam_output = []
    for g in games_without_steam:
        entry = {
            "name": g["name"],
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
        no_steam_output.append(entry)

    # Write output
    output = {
        "steam_games": steam_games_output,
        "no_steam_id": no_steam_output
    }

    os.makedirs("data", exist_ok=True)
    with open("data/igdb.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nComplete!")
    print(f"Wrote {len(steam_games_output)} Steam games to data/igdb.json")
    print(f"Wrote {len(no_steam_output)} non-Steam games to data/igdb.json")

if __name__ == "__main__":
    main()
