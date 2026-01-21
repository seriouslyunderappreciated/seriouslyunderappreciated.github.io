import os
import requests
import time
import json

# Configuration and IDs
# PC: 6, Switch 2: 438, Switch: 130
PLATFORMS = {"PC": 6, "Switch 2": 438, "Switch": 130}
EXCLUDE_THEMES = [19]        # 19: Horror
EXCLUDE_GENRES = [14, 26, 13]    # 14: Sport, 26: Quiz/Trivia, 13: Simulator

def fetch_igdb_data():
    # Retrieve secrets from environment variables
    client_id = os.environ.get('IGDB_CLIENT_ID')
    client_secret = os.environ.get('IGDB_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("Error: Missing IGDB_CLIENT_ID or IGDB_CLIENT_SECRET environment variables.")
        return

    # 1. Get Twitch Access Token
    auth_url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
    auth_response = requests.post(auth_url)
    auth_response.raise_for_status()
    access_token = auth_response.json()['access_token']

    # 2. Setup Timestamps (Last 30 Days)
    now = int(time.time())
    thirty_days_ago = now - (30 * 86400)

    # 3. Build the APICalypse Query
    headers = {
        'Client-ID': client_id,
        'Authorization': f'Bearer {access_token}'
    }
    
    query = f"""
    fields name, first_release_date, platforms.id, platforms.name, cover.url, websites.url, websites.category;
    where first_release_date > {thirty_days_ago} 
    & first_release_date <= {now}
    & platforms = ({",".join(map(str, PLATFORMS.values()))})
    & game_modes = (1)
    & (follows > 20 | popularity > 15)
    & themes != ({",".join(map(str, EXCLUDE_THEMES))})
    & genres != ({",".join(map(str, EXCLUDE_GENRES))})
    & category = (0, 8, 9)
    & cover != null;
    sort first_release_date desc;
    limit 50;
    """

    response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=query)
    response.raise_for_status()
    games = response.json()

    # 4. Process and Filter the Results
    processed_list = []
    for g in games:
        # Platform Priority logic
        available_ids = [p['id'] for p in g.get('platforms', [])]
        
        if PLATFORMS['PC'] in available_ids:
            selected_platform = "PC"
        elif PLATFORMS['Switch 2'] in available_ids:
            selected_platform = "Nintendo Switch 2"
        else:
            selected_platform = "Nintendo Switch"

        # Image formatting (t_thumb -> t_cover_big)
        cover_url = g['cover']['url']
        formatted_cover = "https:" + cover_url.replace('t_thumb', 't_cover_big')

        # Extract Steam link (Website Category 13)
        steam_url = next((w['url'] for w in g.get('websites', []) if w['category'] == 13), None)

        processed_list.append({
            "name": g['name'],
            "release_date": g['first_release_date'],
            "platform": selected_platform,
            "cover_url": formatted_cover,
            "store_url": steam_url
        })

    # 5. Save to data/igdb.json
    output_dir = 'data'
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, 'igdb.json')

    with open(output_path, 'w') as f:
        json.dump(processed_list, f, indent=2)
    
    print(f"Success: Processed {len(processed_list)} games and saved to {output_path}")

if __name__ == "__main__":
    fetch_igdb_data()
