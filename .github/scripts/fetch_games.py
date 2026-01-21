import os
import json
import requests

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

def fetch_game_data(game_id, access_token, client_id):
    """Fetch comprehensive data for a single game."""
    url = "https://api.igdb.com/v4/games"
    
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    # Request all available fields for the game
    # Using * to get all fields and expanding related entities
    query = f"""
    fields *,
        age_ratings.*,
        alternative_names.*,
        artworks.*,
        bundles.*,
        collection.*,
        cover.*,
        dlcs.*,
        expansions.*,
        external_games.*,
        franchise.*,
        franchises.*,
        game_engines.*,
        game_modes.*,
        genres.*,
        involved_companies.company.*,
        involved_companies.*,
        keywords.*,
        multiplayer_modes.*,
        parent_game.*,
        platforms.*,
        player_perspectives.*,
        release_dates.*,
        remakes.*,
        remasters.*,
        screenshots.*,
        similar_games.*,
        standalone_expansions.*,
        themes.*,
        videos.*,
        websites.*;
    where id = {game_id};
    """
    
    response = requests.post(url, headers=headers, data=query)
    response.raise_for_status()
    return response.json()

def main():
    # Get credentials from environment variables (GitHub secrets)
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")
    
    # Get access token
    print("Getting access token...")
    access_token = get_access_token(client_id, client_secret)
    
    # Fetch data for a specific game (example: The Witcher 3 = 1942)
    # You can change this to any game ID you want to test with
    game_id = 1942
    
    print(f"Fetching data for game ID {game_id}...")
    game_data = fetch_game_data(game_id, access_token, client_id)
    
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    
    # Write to file
    output_path = "data/igdb.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(game_data, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully wrote data to {output_path}")
    print(f"Retrieved {len(game_data)} game(s)")

if __name__ == "__main__":
    main()
