import os
import requests
import time
import json

def fetch_games():
    # 1️⃣ Auth
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

    # 2️⃣ Time window: last 30 days
    now = int(time.time())
    thirty_days_ago = now - 30 * 86400

    # 3️⃣ Query
    query = (
        "fields id, name, first_release_date, platforms.id, platforms.name, "
        "cover.url, follows, rating, rating_count, aggregated_rating, aggregated_rating_count; "
        f"where first_release_date > {thirty_days_ago} "
        f"& first_release_date <= {now} "
        "& platforms = (6,130,438) "
        "& category = (0) "
        "& (follows > 3 | rating_count > 10 | aggregated_rating_count > 5); "
        "sort first_release_date desc; "
        "limit 50;"
    )

    # 4️⃣ Request
    res = requests.post(
        "https://api.igdb.com/v4/games",
        headers=headers,
        data=query,
    )
    res.raise_for_status()

    games = res.json()

    # 5️⃣ Save JSON
    os.makedirs("data", exist_ok=True)
    with open("data/igdb.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)

    print(f"Wrote {len(games)} games to data/igdb.json")

if __name__ == "__main__":
    fetch_games()
