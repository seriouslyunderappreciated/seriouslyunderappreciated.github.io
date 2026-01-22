import os
import json
import requests
from datetime import datetime, timedelta

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
    """Fetch games matching our criteria (without sorting by popularity yet)."""
    ninety_days_ago = int((datetime.now() - timedelta(days=90)).timestamp())
    current_time = int(datetime.now().timestamp())
    
    # Platform IDs: 6 = PC (Windows), 130 = Nintendo Switch, 471 = Nintendo Switch 2
    # Game modes: 1 = Single player
    # Game type: 0 = main_game
    # Genres to exclude: 14 = Sport, 26 = Quiz/Trivia, 13 = Simulator
    # Themes to exclude: 19 = Horror
    
    query = f"""
    fields id, name, platforms, cover, genres, themes;
    where first_release_date >= {ninety_days_ago}
      & first_release_date <= {current_time}
      & platforms = (6, 130, 471)
      & game_modes = 1
      & game_type = 0
      & genres != (14, 26, 13)
      & themes != 19;
    limit 500;
    """
    
    return make_igdb_request("games", query, access_token, client_id)

def get_popularity_scores(game_ids, access_token, client_id):
    """Fetch popularity scores for given game IDs (types 2 and 6)."""
    ids_string = ",".join(map(str, game_ids))
    
    # Fetch popularity_type 2
    query_type2 = f"""
    fields game_id, value;
    where game_id = ({ids_string}) & popularity_type = 2;
    """
    results_type2 = make_igdb_request("popularity_primitives", query_type2, access_token, client_id)
    
    # Fetch popularity_type 6
    query_type6 = f"""
    fields game_id, value;
    where game_id = ({ids_string}) & popularity_type = 6;
    """
    results_type6 = make_igdb_request("popularity_primitives", query_type6, access_token, client_id)
    
    # Store scores separately and calculate total
    popularity_data = {}
    
    for item in results_type2:
        game_id = item["game_id"]
        if game_id not in popularity_data:
            popularity_data[game_id] = {"type_2": 0, "type_6": 0, "total": 0}
        popularity_data[game_id]["type_2"] = item["value"]
        popularity_data[game_id]["total"] += item["value"]
    
    for item in results_type6:
        game_id = item["game_id"]
        if game_id not in popularity_data:
            popularity_data[game_id] = {"type_2": 0, "type_6": 0, "total": 0}
        popularity_data[game_id]["type_6"] = item["value"]
        popularity_data[game_id]["total"] += item["value"]
    
    return popularity_data

def get_platforms_data(platform_ids, access_token, client_id):
    """Fetch platform names for given platform IDs."""
    ids_string = ",".join(map(str, platform_ids))
    query = f"""
    fields name;
    where id = ({ids_string});
    """
    
    platforms = make_igdb_request("platforms", query, access_token, client_id)
    return {p["id"]: p["name"] for p in platforms}

def get_covers_data(cover_ids, access_token, client_id):
    """Fetch cover image data for given cover IDs."""
    ids_string = ",".join(map(str, cover_ids))
    query = f"""
    fields image_id;
    where id = ({ids_string});
    """
    
    covers = make_igdb_request("covers", query, access_token, client_id)
    return {c["id"]: c["image_id"] for c in covers}

def get_all_genres(access_token, client_id):
    """Fetch all genres with their IDs and names."""
    query = "fields id, name; limit 500;"
    genres = make_igdb_request("genres", query, access_token, client_id)
    return {g["id"]: g["name"] for g in genres}

def get_all_themes(access_token, client_id):
    """Fetch all themes with their IDs and names."""
    query = "fields id, name; limit 500;"
    themes = make_igdb_request("themes", query, access_token, client_id)
    return {t["id"]: t["name"] for t in themes}

def main():
    # Get credentials from environment variables (GitHub secrets)
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")
    
    # Get access token
    print("Getting access token...")
    access_token = get_access_token(client_id, client_secret)
    
    # Fetch all genres and themes for mapping
    print("Fetching all genres...")
    genres_map = get_all_genres(access_token, client_id)
    
    print("Fetching all themes...")
    themes_map = get_all_themes(access_token, client_id)
    
    # Step 1: Fetch candidate games matching our filters
    print("Fetching candidate games...")
    games = fetch_candidate_games(access_token, client_id)
    
    if not games:
        print("No games found matching criteria")
        return
    
    print(f"Found {len(games)} candidate games")
    
    # Step 2: Get popularity scores for all candidate games
    print("Fetching popularity scores...")
    game_ids = [game["id"] for game in games]
    popularity_data = get_popularity_scores(game_ids, access_token, client_id)
    
    # Step 3: Attach popularity to games and sort
    for game in games:
        game_popularity = popularity_data.get(game["id"], {"type_2": 0, "type_6": 0, "total": 0})
        game["popularity_total"] = game_popularity["total"]
        game["popularity_type_2"] = game_popularity["type_2"]
        game["popularity_type_6"] = game_popularity["type_6"]
    
    # Sort by popularity and take top 10
    games.sort(key=lambda x: x["popularity_total"], reverse=True)
    top_games = games[:10]
    
    print(f"Top 10 most popular games selected")
    
    # Step 4: Collect all unique platform IDs and cover IDs from top 10
    all_platform_ids = set()
    all_cover_ids = []
    
    for game in top_games:
        if "platforms" in game:
            all_platform_ids.update(game["platforms"])
        if "cover" in game:
            all_cover_ids.append(game["cover"])
    
    # Step 5: Fetch platform names
    print("Fetching platform names...")
    platforms_map = get_platforms_data(list(all_platform_ids), access_token, client_id)
    
    # Step 6: Fetch cover image IDs
    print("Fetching cover data...")
    covers_map = get_covers_data(all_cover_ids, access_token, client_id)
    
    # Step 7: Format the final output
    formatted_games = []
    for game in top_games:
        # Build genres list with IDs and names
        genres_list = []
        for genre_id in game.get("genres", []):
            genres_list.append({
                "id": genre_id,
                "name": genres_map.get(genre_id, "Unknown")
            })
        
        # Build themes list with IDs and names
        themes_list = []
        for theme_id in game.get("themes", []):
            themes_list.append({
                "id": theme_id,
                "name": themes_map.get(theme_id, "Unknown")
            })
        
        game_data = {
            "name": game.get("name"),
            "platforms": [platforms_map.get(pid) for pid in game.get("platforms", [])],
            "cover_url": None,
            "genres": genres_list,
            "themes": themes_list,
            "popularity_type_2": game.get("popularity_type_2", 0),
            "popularity_type_6": game.get("popularity_type_6", 0)
        }
        
        # Build cover URL using t_cover_big (264x374px)
        cover_id = game.get("cover")
        if cover_id and cover_id in covers_map:
            image_id = covers_map[cover_id]
            game_data["cover_url"] = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
        
        formatted_games.append(game_data)
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Write to file
    output_path = "data/igdb.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted_games, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully wrote {len(formatted_games)} games to {output_path}")
    for i, game in enumerate(formatted_games, 1):
        print(f"  {i}. {game['name']}")
        print(f"     Genres: {[g['name'] for g in game['genres']]}")
        print(f"     Themes: {[t['name'] for t in game['themes']]}")
        print(f"     Popularity (Type 2): {game['popularity_type_2']}, (Type 6): {game['popularity_type_6']}")

if __name__ == "__main__":
    main()
