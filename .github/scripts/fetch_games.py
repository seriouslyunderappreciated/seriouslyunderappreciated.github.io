import os
import json
import requests
from datetime import datetime, timedelta

# =========================
# CONFIGURABLE CONSTANTS
# =========================
DAYS_AGO = 30      # How many days back to consider games from
TOP_N_HYPES = 30   # Number of games to fetch by hypes before Steam review filtering
TOP_N_FINAL = 6    # Number of final games to include based on Steam total_positive
# =========================

def get_access_token(client_id, client_secret):
    """Get OAuth access token from Twitch."""
    url = "https://id.twitch.tv/oauth2/token"
    params = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }
    response = requests.post(url, params=params)
    response.raise_for_status()
    return response.json()["access_token"]

def make_igdb_request(endpoint, query, access_token, client_id):
    """Make a request to an IGDB endpoint."""
    url = f"https://api.igdb.com/v4/{endpoint}"
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    response = requests.post(url, headers=headers, data=query)
    response.raise_for_status()
    return response.json()

def fetch_candidate_games(access_token, client_id):
    """Fetch candidate games from IGDB."""
    game_age = int((datetime.now() - timedelta(days=DAYS_AGO)).timestamp())
    current_time = int(datetime.now().timestamp())
 
    query = f"""
    fields id, name, platforms, cover, genres, themes, hypes;
    where first_release_date >= {game_age}
      & first_release_date <= {current_time}
      & platforms = 6
      & game_modes = 1
      & game_type = 0
      & genres != 14
      & genres != 26
      & genres != 13
      & themes != 19;
    limit 500;
    """
    return make_igdb_request("games", query, access_token, client_id)

def get_steam_app_ids(game_ids, access_token, client_id):
    """Fetch Steam App IDs (UIDs) for IGDB games."""
    ids_string = ",".join(map(str, game_ids))
    query = f"""
    fields game, uid;
    where game = ({ids_string}) & external_game_source = 1;
    """
    results = make_igdb_request("external_games", query, access_token, client_id)
    return {item["game"]: item["uid"] for item in results}

def get_platforms_data(platform_ids, access_token, client_id):
    ids_string = ",".join(map(str, platform_ids))
    query = f"fields name; where id = ({ids_string});"
    platforms = make_igdb_request("platforms", query, access_token, client_id)
    return {p["id"]: p["name"] for p in platforms}

def get_covers_data(cover_ids, access_token, client_id):
    ids_string = ",".join(map(str, cover_ids))
    query = f"fields image_id; where id = ({ids_string});"
    covers = make_igdb_request("covers", query, access_token, client_id)
    return {c["id"]: c["image_id"] for c in covers}

def get_all_genres(access_token, client_id):
    query = "fields id, name; limit 500;"
    genres = make_igdb_request("genres", query, access_token, client_id)
    return {g["id"]: g["name"] for g in genres}

def get_all_themes(access_token, client_id):
    query = "fields id, name; limit 500;"
    themes = make_igdb_request("themes", query, access_token, client_id)
    return {t["id"]: t["name"] for t in themes}

def fetch_steam_total_positive(steam_appid):
    """Get total_positive reviews from Steam Store API for a given appid."""
    url = f"https://store.steampowered.com/appreviews/{steam_appid}?json=1&language=all&num_per_page=0"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("query_summary", {}).get("total_positive", 0)
    except Exception:
        return 0

def format_game_data(game, genres_map, themes_map, platforms_map, covers_map):
    genres_list = [{"id": gid, "name": genres_map.get(gid, "Unknown")} for gid in game.get("genres", [])]
    themes_list = [{"id": tid, "name": themes_map.get(tid, "Unknown")} for tid in game.get("themes", [])]

    game_data = {
        "name": game.get("name"),
        "platforms": [platforms_map.get(pid) for pid in game.get("platforms", [])],
        "cover_url": None,
        "genres": genres_list,
        "themes": themes_list,
        "hypes": game.get("hypes", 0),
        "steam_appid": game.get("steam_appid"),
        "total_positive": game.get("total_positive", 0)
    }

    cover_id = game.get("cover")
    if cover_id and cover_id in covers_map:
        image_id = covers_map[cover_id]
        game_data["cover_url"] = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

    return game_data

def main():
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")

    print("Getting access token...")
    access_token = get_access_token(client_id, client_secret)

    print("Fetching genres and themes...")
    genres_map = get_all_genres(access_token, client_id)
    themes_map = get_all_themes(access_token, client_id)

    print("Fetching candidate games...")
    games = fetch_candidate_games(access_token, client_id)
    if not games:
        print("No games found matching criteria")
        return

    # Fetch Steam App IDs
    print("Fetching Steam App IDs...")
    game_ids = [game["id"] for game in games]
    steam_map = get_steam_app_ids(game_ids, access_token, client_id)

    # Only keep games with a Steam App ID
    games = [g for g in games if g["id"] in steam_map]
    for game in games:
        game["steam_appid"] = steam_map[game["id"]]
        game["hypes"] = game.get("hypes", 0)

    # Sort by hypes and pick top N_HYPES
    games.sort(key=lambda x: x["hypes"], reverse=True)
    top_hyped = games[:TOP_N_HYPES]

    # Fetch total_positive reviews from Steam for each top game
    print("Fetching total_positive from Steam...")
    for game in top_hyped:
        game["total_positive"] = fetch_steam_total_positive(game["steam_appid"])

    # Sort by total_positive and pick final top N_FINAL
    top_final = sorted(top_hyped, key=lambda x: x["total_positive"], reverse=True)[:TOP_N_FINAL]

    # Collect platform and cover IDs
    all_platform_ids = set()
    all_cover_ids = []
    for g in top_final:
        if "platforms" in g:
            all_platform_ids.update(g["platforms"])
        if "cover" in g:
            all_cover_ids.append(g["cover"])

    platforms_map = get_platforms_data(list(all_platform_ids), access_token, client_id)
    covers_map = get_covers_data(all_cover_ids, access_token, client_id)

    # Format final output
    formatted_games = [format_game_data(g, genres_map, themes_map, platforms_map, covers_map) for g in top_final]

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    # Write single output file
    output_path = "data/igdb.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted_games, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote {len(formatted_games)} games to {output_path}")
    for i, game in enumerate(formatted_games, 1):
        print(f"{i}. {game['name']} - Hypes: {game['hypes']} - Total Positive: {game['total_positive']}")

if __name__ == "__main__":
    main()
