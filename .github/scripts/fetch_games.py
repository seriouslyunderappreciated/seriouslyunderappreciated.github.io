import os
import requests

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

def main():
    client_id = os.getenv("IGDB_CLIENT_ID")
    client_secret = os.getenv("IGDB_CLIENT_SECRET")
    
    access_token = get_access_token(client_id, client_secret)
    
    game_id = 306141
    
    query = f"""
    fields game, uid;
    where game = ({game_id}) & external_game_source = 1;
    """
    
    url = "https://api.igdb.com/v4/external_games"
    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    
    r = requests.post(url, headers=headers, data=query)
    r.raise_for_status()
    
    results = r.json()
    print(f"Results for game {game_id}:")
    print(results)

if __name__ == "__main__":
    main()
