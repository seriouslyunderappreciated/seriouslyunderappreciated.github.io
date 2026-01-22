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
    ninety_days_ago = int((datetime.now() - timedelta(days=90)).timestamp())
    current_time = int(datetime.now().timestamp())

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

def get_platforms_data(platform_ids, access_token, client_id):
    ids_string = ",".join(map(str, platform_ids))
    query = f"""
    fields name;
    where id = ({ids_string});
    """
    platforms = make_igdb_request("platforms", query, access_token, client_id)
    return {p["id"]: p["name"] for p in platforms}

def get_covers_data(cover_ids, access_token, client_id):
    ids_string = ",".join(map(str, cover_ids))
    query = f"""
    fields image_id;
    where id = ({ids_string});
    """
    covers = make_igdb_request("covers", query, access_token, client_id)
    return {c["id"]: c["image_id"] for c in covers}

def get_all_genres(access_token, client_id):
    query = "fields id, name; limit 500;"
    genres = make_igdb_request("genres", query, access_token, client_id)
    return {g["id"]: g["name"] for g in genres}

def get_all_themes(access_token, client_id):
    query = "fields id, name; limit 500;"
    themes = make_igdb_request("themes", query, access_token, client_id)
    return {t["id"]: t["name"] for t in themes}

def main():
    client_id = os.environ.get("IGDB_CLIENT_ID")
    client_secret = os.environ.get("IGDB_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")

    access_token = get_access_token(client_id, client_secret)

    genres_map = get_all_genres(access_token, client_id)
    themes_map = get_all_themes(access_token, client_id)

    games = fetch_candidate_games(access_token, client_id)

    if not games:
        print("No games found matching criteria")
        return

    all_platform_ids = set()
    all_cover_ids = []

    for game in games:
        if "platforms" in game:
            all_platform_ids.update(game["platforms"])
        if "cover" in game:
            all_cover_ids.append(game["cover"])

    platforms_map = get_platforms_data(list(all_platform_ids), access_token, client_id)
    covers_map = get_covers_data(all_cover_ids, access_token, client_id)

    formatted_games = []
    for game in games:
        genres_list = [{"id": gid, "name": genres_map.get(gid, "Unknown")} for gid in game.get("genres", [])]
        themes_list = [{"id": tid, "name": themes_map.get(tid, "Unknown")} for tid in game.get("themes", [])]

        game_data = {
            "name": game.get("name"),
            "platforms": [platforms_map.get(pid) for pid in game.get("platforms", [])],
            "cover_url": None,
            "genres": genres_list,
            "themes": themes_list
        }

        cover_id = game.get("cover")
        if cover_id and cover_id in covers_map:
            image_id = covers_map[cover_id]
            game_data["cover_url"] = f"https://images.igdb.com/igdb/image/upload/t_cover_big/{image_id}.jpg"

        formatted_games.append(game_data)

    os.makedirs("data", exist_ok=True)
    output_path = "data/igdb.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(formatted_games, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote {len(formatted_games)} games to {output_path}")
    for i, game in enumerate(formatted_games, 1):
        print(f"  {i}. {game['name']}")
        print(f"     Genres: {[g['name'] for g in game['genres']]}" )
        print(f"     Themes: {[t['name'] for t in game['themes']]}" )

if __name__ == "__main__":
    main()
