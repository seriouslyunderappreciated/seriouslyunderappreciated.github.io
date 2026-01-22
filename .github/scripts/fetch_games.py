import os
import json
import requests
from datetime import datetime, timedelta

# =========================
# CONFIGURABLE CONSTANTS
# =========================
DAYS_AGO = 30           # How many days back to consider games from
TOP_N = 5               # Number of top games for each list
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
    """Fetch games matching our criteria."""
    game_age = int((datetime.now() - timedelta(days=DAYS_AGO)).timestamp())
    current_time = int(datetime.now().timestamp())
    
    query = f"""
    fields id, name, platforms, cover, genres, themes, hypes;
    where first_release_date >= {game_age}
      & first_release_date <= {current_time}
      & platforms = (6)
      & game_modes = (1)
      & game_type = 0
      & genres != (14, 26, 13)
      & themes != (19);
    limit 500;
    """
    return make_igdb_request("games", query, access_token, client_id)

def get_steam_app_ids(game_ids, access_token, client_id):
    """Fetch Steam App IDs for given IGDB game IDs."""
    ids_string = ",".join(map(str, game_ids))
    query = f"""
    fields game, uid;
    where game = ({ids_string}) & external_game_source = 1;
    """
    results = make_igdb_request("external_games", query, access_token, client_id)
    steam_map = {item["game"]: item["uid"] for item in results}
    return steam_map

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
        "steam_appid": game.get("steam_appid")
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
    
    print("Fetching Steam App IDs...")
    game_ids = [game["id"] for game in games]
    steam_map = get_steam_app_ids(game_ids, access_token, client_id)
    
    for game in games:
        game["steam_appid"] = steam_map.get(game["id"])
        game["hypes"] = game.get("hypes", 0)
    
    # Separate into Steam and Non-Steam
    steam_games = [g for g in games if g["steam_appid"]]
    non_steam_games = [g for g in games if not g["steam_appid"]]
    
    # Sort by hypes
    steam_games.sort(key=lambda x: x["hypes"], reverse=True)
    non_steam_games.sort(key=lambda x: x["hypes"], reverse=True)
    
    # Take top N from each
    top_steam = steam_games[:TOP_N]
    top_non_steam = non_steam_games[:TOP_N]
    
    # Collect platform and cover IDs
    all_platform_ids = set()
    all_cover_ids = []
    for g in top_steam + top_non_steam:
        if "platforms" in g:
            all_platform_ids.update(g["platforms"])
        if "cover" in g:
            all_cover_ids.append(g["cover"])
    
    platforms_map = get_platforms_data(list(all_platform_ids), access_token, client_id)
    covers_map = get_covers_data(all_cover_ids, access_token, client_id)
    
    # Format games
    formatted_steam = [format_game_data(g, genres_map, themes_map, platforms_map, covers_map) for g in top_steam]
    formatted_non_steam = [format_game_data(g, genres_map, themes_map, platforms_map, covers_map) for g in top_non_steam]
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Write outputs
    with open("data/steam_top.json", "w", encoding="utf-8") as f:
        json.dump(formatted_steam, f, indent=2, ensure_ascii=False)
    
    with open("data/igdb_top.json", "w", encoding="utf-8") as f:
        json.dump(formatted_non_steam, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully wrote {len(formatted_steam)} Steam games to data/steam_top.json")
    print(f"Successfully wrote {len(formatted_non_steam)} Non-Steam games to data/igdb_top.json")

if __name__ == "__main__":
    main()
