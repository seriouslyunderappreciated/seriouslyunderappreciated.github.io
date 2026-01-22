import os
import json
import requests
from datetime import datetime, timedelta

def get_access_token(client_id, client_secret):
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
    # Changed to 30 days
    thirty_days_ago = int((datetime.now() - timedelta(days=30)).timestamp())
    current_time = int(datetime.now().timestamp())
    
    # Platforms: 6 = PC only
    query = f"""
    fields id, name, platforms, cover, genres, themes;
    where first_release_date >= {thirty_days_ago}
      & first_release_date <= {current_time}
      & platforms = (6)
      & game_modes = 1
      & game_type = 0
      & genres != (14, 26, 13)
      & themes != 19;
    limit 500;
    """
    return make_igdb_request("games", query, access_token, client_id)

def get_steam_ids(game_ids, access_token, client_id):
    """Fetch Steam AppIDs (external_game_source = 1)."""
    ids_string = ",".join(map(str, game_ids))
    query = f"""
    fields game, uid;
    where game = ({ids_string}) & category = 1;
    limit 500;
    """
    results = make_igdb_request("external_games", query, access_token, client_id)
    # Map game_id to steam_uid
    return {item["game"]: item["uid"] for item in results}

def get_popularity_scores(game_ids, access_token, client_id):
    """Fetch only popularity_type 2."""
    ids_string = ",".join(map(str, game_ids))
    query = f"""
    fields game_id, value;
    where game_id = ({ids_string}) & popularity_type = 2;
    """
    results = make_igdb_request("popularity_primitives", query, access_token, client_id)
    return {item["game_id"]: item["value"] for item in results}

# ... (get_platforms_data, get_covers_data, get_all_genres, get_all_themes remain similar) ...

def main():
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")
    
    access_token = get_access_token(client_id, client_secret)
    genres_map = get_all_genres(access_token, client_id)
    themes_map = get_all_themes(access_token, client_id)
    
    print("Fetching candidate PC games (last 30 days)...")
    games = fetch_candidate_games(access_token, client_id)
    
    if not games:
        print("No games found.")
        return

    game_ids = [game["id"] for game in games]

    # Fetch Steam IDs
    print("Fetching Steam AppIDs...")
    steam_map = get_steam_ids(game_ids, access_token, client_id)

    # Fetch Popularity (Type 2 only)
    print("Fetching popularity (Type 2)...")
    popularity_map = get_popularity_scores(game_ids, access_token, client_id)
    
    # Attach data and sort
    for game in games:
        game["steam_appid"] = steam_map.get(game["id"])
        game["popularity_type_2"] = popularity_map.get(game["id"], 0)
    
    games.sort(key=lambda x: x["popularity_type_2"], reverse=True)
    top_games = games[:10]
    
    # Enrichment calls (Covers/Platforms)
    all_cover_ids = [g["cover"] for g in top_games if "cover" in g]
    covers_map = get_covers_data(all_cover_ids, access_token, client_id) if all_cover_ids else {}

    formatted_games = []
    for game in top_games:
        game_data = {
            "name": game.get("name"),
            "steam_appid": game.get("steam_appid"),
            "popularity_score": game.get("popularity_type_2"),
            "cover_url": f"https://images.igdb.com/igdb/image/upload/t_cover_big/{covers_map[game['cover']]}.jpg" if game.get("cover") in covers_map else None,
            "genres": [genres_map.get(gid, "Unknown") for gid in game.get("genres", [])],
            "themes": [themes_map.get(tid, "Unknown") for tid in game.get("themes", [])]
        }
        formatted_games.append(game_data)
    
    os.makedirs("data", exist_ok=True)
    with open("data/igdb.json", "w", encoding="utf-8") as f:
        json.dump(formatted_games, f, indent=2, ensure_ascii=False)
    
    print(f"Done. Saved {len(formatted_games)} games.")

if __name__ == "__main__":
    main()
