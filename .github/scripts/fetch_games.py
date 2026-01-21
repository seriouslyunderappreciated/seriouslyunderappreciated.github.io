import os
import requests
import time
import json

def fetch_games():
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

    now = int(time.time())
    thirty_days_ago = now - 30 * 86400

    query = (
        "fields id, name, first_release_date; "
        f"where first_release_date > {thirty_days_ago} "
        f"& first_release_date <= {now}; "
        "limit 50;"
    )

    res = requests.post(
        "https://api.igdb.com/v4/games",
        headers=headers,
        data=query,
    )
    res.raise_for_status()

    games = res.json()

    os.makedirs("data", exist_ok=True)
    with open("data/igdb.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)

    print(f"Wrote {len(games)} games to data/igdb.json")

if __name__ == "__main__":
    fetch_games()
