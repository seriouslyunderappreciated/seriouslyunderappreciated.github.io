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
    
    # Platform IDs: 6 = PC (Windows), 130 = Nintendo Switch, 471 = Nintendo Switch 2
    # Game modes: 1 = Single player
    # Category: 0 = main_game
    # Genres to exclude: 14 = Sport, 26 = Quiz/Trivia, 13 = Simulator
    # Themes to exclude: 19 = Horror
    
    query = f"""
    fields id, name, platforms, cover;
    where first_release_date >= {ninety_days_ago}
      & platforms = (6, 130, 471)
      & game_modes = 1
      & category = 0
      & genres != (14, 26, 13)
      & themes != 19;
    limit 500;
    """
    
    return make_igdb_request("games", query, access_token, client_id)

def get_popularity_scores(game_ids, access_token, client_id):
    """Fetch popularity scores for given game IDs."""
    ids_string = ",".join(map(str, game_ids))
    query = f"""
    fields game_id, value;
    where game_id = ({ids_string}) & popularity_type = 1;
    """
    
    results = make_igdb_request("popularity_primitives", query, access_token, client_id)
    return {item["game_id"]: item["value"] for item in results}

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

def main():
    # Get credentials from environment variables (GitHub secrets)
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")
    
    # Get access token
    print("Getting access token...")
    access_token = get_access_token(client_id, client_secret)
    
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
    popularity_scores = get_popularity_scores(game_ids, access_token, client_id)
    
    # Step 3: Attach popularity to games and sort
    for game in games:
        game["popularity"] = popularity_scores.get(game["id"], 0)
    
    # Sort by popularity and take top 10
    games.sort(key=lambda x: x["popularity"], reverse=True)
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
        game_data = {
            "name": game.get("name"),
            "platforms": [platforms_map.get(pid) for pid in game.get("platforms", [])],
            "cover_url": None
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

if __name__ == "__main__":
    main()
