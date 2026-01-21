import os, requests, time, json

# IDs from our discussion
PLATFORMS = {"PC": 6, "Switch 2": 438, "Switch": 130}
EXCLUDE_THEMES = [19]      # Horror
EXCLUDE_GENRES = [14, 26, 13]  # Sport, Quiz, Simulator

def get_data():
    client_id = os.environ['IGDB_CLIENT_ID']
    client_secret = os.environ['IGDB_CLIENT_SECRET']
    
    # 1. Get Access Token
    auth = requests.post(f"https://id.twitch.tv/oauth2/token?client_id={client_id}&client_secret={client_secret}&grant_type=client_credentials")
    token = auth.json()['access_token']
    
    # 2. Prepare Query
    now = int(time.time())
    thirty_days_ago = now - (30 * 86400)
    
    headers = {'Client-ID': client_id, 'Authorization': f'Bearer {token}'}
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
    games = response.json()
    
    processed = []
    for g in games:
        # Platform Priority Logic
        p_ids = [p['id'] for p in g['platforms']]
        if PLATFORMS['PC'] in p_ids:
            best_p = "PC"
        elif PLATFORMS['Switch 2'] in p_ids:
            best_p = "Nintendo Switch 2"
        else:
            best_p = "Nintendo Switch"
            
        # Image URL Formatting
        cover = "https:" + g['cover']['url'].replace('t_thumb', 't_cover_big')
        
        # Find Steam Link (Category 13)
        store = next((w['url'] for w in g.get('websites', []) if w['category'] == 13), None)
        
        processed.append({
            "name": g['name'],
            "release_date": g['first_release_date'],
            "platform": best_p,
            "cover_url": cover,
            "store_url": store
        })
        
    with open('games.json', 'w') as f:
        json.dump(processed, f, indent=2)

if __name__ == "__main__":
    get_data()
