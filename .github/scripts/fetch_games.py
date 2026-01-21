import os
import requests
import json

def fetch_debug_data():
    client_id = os.environ.get('IGDB_CLIENT_ID')
    client_secret = os.environ.get('IGDB_CLIENT_SECRET')

    # 1. Get Token
    auth_url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
    auth_response = requests.post(auth_url)
    auth_response.raise_for_status()
    access_token = auth_response.json()['access_token']
    print("Step 1: Successfully authenticated with Twitch.")

    # 2. Simplest Possible Query (Get 'Hades' by ID)
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    # We are asking for 1 game, no complex filters
    query = "fields name; where id = 113112;"

    print(f"Step 2: Sending query: {query}")
    response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=query)
    
    # If this fails, this print will tell us EXACTLY why (e.g., "Syntax error on line 1")
    if response.status_code != 200:
        print(f"IGDB ERROR: {response.status_code}")
        print(f"RESPONSE BODY: {response.text}")
        response.raise_for_status()

    games = response.json()
    print(f"Step 3: Received data: {games}")

    # 3. Save to data/igdb.json
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'igdb.json')

    with open(output_path, 'w') as f:
        json.dump(games, f, indent=2)
    
    print(f"Step 4: Successfully saved to {output_path}")

if __name__ == "__main__":
    fetch_debug_data()
