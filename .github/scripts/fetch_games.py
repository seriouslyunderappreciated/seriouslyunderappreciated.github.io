import os
import requests
import json

def fetch_game_by_id():
    client_id = os.environ["IGDB_CLIENT_ID"]
    client_secret = os.environ["IGDB_CLIENT_SECRET"]

    auth = requests.post(
        f"https://id.twitch.tv/oauth2/token"
        f"?client_id={client_id}"
        f"&client_secret={client_secret}"
        f"&grant_type=client_credentials"
    )
    auth.raise_for_status()
    token = auth.json()["access_token"]

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    query = "fields *; where id = 1942;"

    res = requests.post(
        "https://api.igdb.com/v4/games",
        headers=headers,
        data=query
    )
    res.raise_for_status()

    games = res.json()

    import os
    os.makedirs("data", exist_ok=True)
    with open("data/igdb.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Fetched {len(games)} game(s). Saved to data/igdb.json")

if __name__ == "__main__":
    fetch_game_by_id()
