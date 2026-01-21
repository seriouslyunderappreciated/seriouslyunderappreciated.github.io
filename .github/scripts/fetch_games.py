import os
import requests
import time
import json

# Configuration IDs
PLATFORMS = [6, 130, 438]        # PC, Switch, Switch 2
EXCLUDE_THEMES = [19, 42]        # Horror, Erotica
EXCLUDE_GENRES = [14, 26, 13]    # Sport, Quiz, Simulator

def fetch_igdb_data():
    client_id = os.environ.get('IGDB_CLIENT_ID')
    client_secret = os.environ.get('IGDB_CLIENT_SECRET')

    # 1. Get Token
    auth_url = f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials"
    auth_res = requests.post(auth_url)
    auth_res.raise_for_status()
    token = auth_res.json()['access_token']

    # 2. Time Logic
    now = int(time.time())
    thirty_days_ago = now - (30 * 86400)

    # 3. Build Query - String formatted for absolute safety
    headers = {'Client-ID': client_id, 'Authorization': f'Bearer {token}'}
    
    # We join our lists into comma-separated strings for the query
    p_str = ",".join(map(str, PLATFORMS))
    t_str = ",".join(map(str, EXCLUDE_THEMES))
    g_str = ",".join(map(str, EXCLUDE_GENRES))

    # Note: Using & to separate conditions and () for sets
    query = (
        f"fields name, first_release_date, platforms.id, platforms.name, cover.url, websites.url, websites.category; "
        f"where first_release_date > {thirty_days_ago} & first_release_date <= {now} "
        f"& platforms = ({p_str}) "
        f"& game_modes = (1) "
        f"& (follows > 15 | popularity > 10) "
        f"& themes != ({t_str}) "
        f"& genres != ({g_str}) "
        f"& category = (0, 8, 9) "
        f"& cover != null; "
        f"sort first_release_date desc; "
        f"limit 50;"
    )

    response = requests.post("https://api.igdb.com/v4/games", headers=headers, data=query)
    
    if response.status_code != 200:
        print(f"Query Error: {response.text}") # This will show the syntax error if one occurs
        response.raise_for_status()

    games = response.json()
    processed = []

    for g in games:
        # Priority: PC (6) > Switch 2 (438) > Switch (130)
        p_ids = [p['id'] for p in g.get('platforms', [])]
        if 6 in p_ids:
            p_name = "PC"
        elif 438 in p_ids:
            p_name = "Nintendo Switch 2"
        else:
            p_name = "Nintendo Switch"

        # Image Logic
        cover = "https:" + g['cover']['url'].replace('t_thumb', 't_cover_big') if 'cover' in g else None
        
        # Steam Link Logic (Category 13 is Steam)
        steam = next((w['url'] for w in g.get('websites', []) if w.get('category') == 13), None)

        processed.append({
            "name": g['name'],
            "date": g['first_release_date'],
            "platform": p_name,
            "cover": cover,
            "url": steam
        })

    # 4. Save to data/igdb.json
    os.makedirs('data', exist_ok=True)
    with open('data/igdb.json', 'w') as f:
        json.dump(processed, f, indent=2)
    
    print(f"Successfully processed {len(processed)} high-quality games.")

if __name__ == "__main__":
    fetch_igdb_data()
