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

def fetch_popular_games(access_token, client_id):
    """Fetch top 10 popular single-player games from last 90 days."""
    url = "https://api.igdb.com/v4/games"
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Calculate date 90 days ago (Unix timestamp)
    ninety_days_ago = int((datetime.now() - timedelta(days=90)).timestamp())
    
    # Platform IDs:
    # 6 = PC (Windows)
    # 130 = Nintendo Switch
    # 471 = Nintendo Switch 2
    
    # Game modes:
    # 1 = Single player
    
    # Genres to exclude:
    # 4 = Fighting (not needed but keeping note)
    # 5 = Shooter (not needed)
    # 14 = Sport
    # 16 = Turn-based strategy (not needed)
    # 26 = Quiz/Trivia
    # 19 = Horror (actually called "Horror" but ID might be different)
    # 14 = Sport
    # 13 = Simulator
    
    # Game category:
    # 0 = main_game
    # (1 = dlc, 2 = expansion, 3 = bundle, etc.)
    
    query = f"""
    fields name, platforms.name, cover.image_id, cover.url;
    where first_release_date >= {ninety_days_ago}
      & platforms = (6, 130, 471)
      & game_modes = (1)
      & category = 0
      & genres != (14, 26, 13, 19);
    sort popularity desc;
    limit 10;
    """
    
    response = requests.post(url, headers=headers, data=query)
    response.raise_for_status()
    games = response.json()
    
    # Format the data with proper cover URLs
    formatted_games = []
    for game in games:
        game_data = {
            "name": game.get("name"),
            "platforms": [p.get("name") for p in game.get("platforms", [])],
            "cover_url": None
        }
        
        # Build cover URL (using t_cover_big which is 264x374px - closest to 320px height)
        if game.get("cover") and game["cover"].get("image_id"):
            image_id = game["cover"]["image_id"]
            game_data["cover_url"] = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"
        
        formatted_games.append(game_data)
    
    return formatted_games

def main():
    # Get credentials from environment variables (GitHub secrets)
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")
    
    # Get access token
    print("Getting access token...")
    access_token = get_access_token(client_id, client_secret)
    
    # Fetch popular games
    print("Fetching popular games from last 90 days...")
    games = fetch_popular_games(access_token, client_id)
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Write to file
    output_path = "data/igdb.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully wrote {len(games)} games to {output_path}")
    for game in games:
        print(f"  - {game['name']}")

if __name__ == "__main__":
    main()
