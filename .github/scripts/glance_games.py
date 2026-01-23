import requests
import re
import json
import time
import os
from pathlib import Path

# ============ CONFIGURATION ============
TOP_N_GAMES = 6  # Number of top games to output
INITIAL_POOL_SIZE = 40  # Number of games to fetch from Steam search
REQUEST_DELAY = 0.5  # Delay between review API requests (seconds) to avoid rate limiting

# Steam search URL with your filters
SEARCH_URL = (
    "https://store.steampowered.com/search/results/"
    "?sort_by=Released_DESC"
    "&json=1"
    "&untags=599,701,5055,1667,3978,1100689,24904,3799,1666,1663,10437,21978,"
    "615955,10383,1084988,1100687,255534,699,4102,1665,4885,4255,5395,5537,1664,"
    "493,1770,353880,597,1718"
    "&category1=998"
    "&category3=2"
    "&controllersupport=18"
    "&supportedlang=english"
    "&hidef2p=1"
    "&filter=topsellers"
    "&ndl=1"
    f"&count={INITIAL_POOL_SIZE}"
)

def extract_appid_from_logo(logo_url):
    """Extract appid from Steam logo URL."""
    match = re.search(r"steam/\w+/(\d+)", logo_url)
    if match:
        return match.group(1)
    return None

def get_review_count(appid):
    """Fetch total positive reviews for a given appid."""
    url = f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all&num_per_page=0"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("success") == 1:
            query_summary = data.get("query_summary", {})
            return query_summary.get("total_positive", 0)
        return 0
    except Exception as e:
        print(f"  ⚠️  Error fetching reviews for appid {appid}: {e}")
        return 0

def main():
    print("🎮 Steam Top Recent Games Scraper")
    print("=" * 50)
    
    # Step 1: Fetch initial pool of games
    print(f"\n📥 Fetching {INITIAL_POOL_SIZE} recently released games...")
    try:
        response = requests.get(SEARCH_URL, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Error fetching search results: {e}")
        return
    
    items = data.get("items", [])
    if not items:
        print("❌ No games found in search results!")
        return
    
    print(f"✅ Found {len(items)} games")
    
    # Step 2: Extract appids and fetch review counts
    print(f"\n📊 Fetching review counts for each game...")
    games_with_reviews = []
    
    for i, item in enumerate(items, 1):
        name = item.get("name", "Unknown")
        logo = item.get("logo", "")
        
        appid = extract_appid_from_logo(logo)
        if not appid:
            print(f"  ⚠️  [{i}/{len(items)}] Skipping '{name}' - couldn't extract appid")
            continue
        
        print(f"  🔍 [{i}/{len(items)}] {name} (appid: {appid})")
        
        total_positive = get_review_count(appid)
        
        games_with_reviews.append({
            "appid": appid,
            "name": name,
            "total_positive": total_positive
        })
        
        # Rate limiting delay
        if i < len(items):
            time.sleep(REQUEST_DELAY)
    
    # Step 3: Sort by positive reviews (descending)
    print(f"\n📈 Sorting games by positive review count...")
    games_with_reviews.sort(key=lambda x: x["total_positive"], reverse=True)
    
    # Step 4: Take top N games
    top_games = games_with_reviews[:TOP_N_GAMES]
    
    # Step 5: Save to JSON
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "top_recent.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(top_games, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved top {len(top_games)} games to {output_file}")
    
    # Display results
    print(f"\n🏆 Top {len(top_games)} Recent Games by Positive Reviews:")
    print("=" * 70)
    for i, game in enumerate(top_games, 1):
        print(f"{i:2d}. {game['name']:<50} | 👍 {game['total_positive']:>7,} | ID: {game['appid']}")
    
    print(f"\n✨ Done! Check {output_file} for the full data.")

if __name__ == "__main__":
    main()
