import requests
import re
import json
import time
import os
from pathlib import Path

# ============ CONFIGURATION ============
TOP_N_GAMES = 3
INITIAL_POOL_SIZE = 100
REQUEST_DELAY = 0.5  # Delay for review API
STEAMCMD_DELAY = 0.5 # Delay for SteamCMD API to be respectful
APPDETAILS_DELAY = 0.5  # Delay for appdetails API
MIN_REVIEWS = 1600  # Minimum total reviews to be considered
MIN_RATIO = 0.90  # Minimum positive ratio to be considered
MAX_REVIEW_COUNT = 2000  # Cap for review count in weighted score calculation

# Excluded genres and categories (by description)
EXCLUDED_GENRES = ["Early Access"]
EXCLUDED_CATEGORIES = []

SEARCH_URL = (
    "https://store.steampowered.com/search/results/"
    "?sort_by=Released_DESC"
    "&json=1"
    "&untags=599,701,5055,1667,3978,1100689,24904,3799,1666,1663,10437,21978,"
    "615955,10383,1084988,1100687,255534,699,4102,1665,4885,4255,5395,5537,1664,"
    "493,1770,353880,597,1718,1645,1754"
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
    match = re.search(r"steam/\w+/(\d+)", logo_url)
    if match:
        return match.group(1)
    return None

def get_review_data(appid):
    url = f"https://store.steampowered.com/appreviews/{appid}?json=1&language=all&num_per_page=0"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("success") == 1:
            query_summary = data.get("query_summary", {})
            return query_summary.get("total_positive", 0), query_summary.get("total_negative", 0)
        return 0, 0
    except Exception:
        return 0, 0

def get_steamcmd_cover(appid):
    """Fetch the library capsule image from SteamCMD API."""
    url = f"https://api.steamcmd.net/v1/info/{appid}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Navigate the JSON structure provided in your example
        # data -> data -> {appid} -> common -> library_assets_full -> library_capsule -> image -> english
        app_data = data.get("data", {}).get(str(appid), {})
        capsule_path = (
            app_data.get("common", {})
            .get("library_assets_full", {})
            .get("library_capsule", {})
            .get("image", {})
            .get("english")
        )
        
        if capsule_path:
            return f"https://shared.fastly.steamstatic.com/store_item_assets/steam/apps/{appid}/{capsule_path}"
    except Exception as e:
        print(f"    ⚠️  Error fetching SteamCMD data for {appid}: {e}")
    
    return None

def check_excluded_content(appid):
    """Check if game has excluded genres or categories. Returns True if should be excluded."""
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Navigate to the app data
        app_data = data.get(str(appid), {})
        if not app_data.get("success"):
            return False
        
        game_data = app_data.get("data", {})
        
        # Check genres
        genres = game_data.get("genres", [])
        for genre in genres:
            if genre.get("description") in EXCLUDED_GENRES:
                return True
        
        # Check categories
        categories = game_data.get("categories", [])
        for category in categories:
            if category.get("description") in EXCLUDED_CATEGORIES:
                return True
        
        return False
    except Exception as e:
        print(f"    ⚠️  Error checking excluded content for {appid}: {e}")
        return False

def main():
    print("🎮 Steam Top Recent Games Scraper")
    print("=" * 50)
    
    # Step 1: Fetch initial pool
    try:
        response = requests.get(SEARCH_URL, timeout=15)
        response.raise_for_status()
        items = response.json().get("items", [])
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # Step 2: Fetch reviews and calculate weighted scores
    print(f"\n📊 Fetching reviews for {len(items)} games...")
    games_with_reviews = []
    for i, item in enumerate(items, 1):
        appid = extract_appid_from_logo(item.get("logo", ""))
        name = item.get("name", "Unknown")
        
        if not appid:
            print(f"  [{i}/{len(items)}] ⚠️  Skipping {name} (no AppID)")
            continue
        
        print(f"  [{i}/{len(items)}] Checking: {name}")
        
        # Check for excluded content (genres/categories)
        if check_excluded_content(appid):
            print(f"            ❌ Excluded (matches excluded genres/categories)")
            time.sleep(APPDETAILS_DELAY)
            continue
        
        pos, neg = get_review_data(appid)
        total = pos + neg
        
        # Skip games with no reviews
        if total == 0:
            print(f"            ❌ No reviews")
            continue
        
        # Filter out games below minimum review threshold
        if total < MIN_REVIEWS:
            print(f"            ❌ Only {total} reviews (below {MIN_REVIEWS} threshold)")
            continue
            
        ratio = pos / total
        
        # Filter out games below ratio threshold
        if ratio < MIN_RATIO:
            print(f"            ❌ {ratio:.1%} rating (below {MIN_RATIO:.0%} threshold)")
            continue
        
        # Calculate weighted score: min(total reviews, cap) × ratio
        capped_reviews = min(total, MAX_REVIEW_COUNT)
        weighted_score = capped_reviews * ratio
        
        print(f"            ✅ {ratio:.1%} with {total} reviews → score: {weighted_score:.0f}")
        
        games_with_reviews.append({
            "appid": appid,
            "name": name,
            "total_reviews": total,
            "total_positive": pos,
            "ratio": ratio,
            "weighted_score": weighted_score
        })
        time.sleep(REQUEST_DELAY)

    # Step 3 & 4: Sort by weighted score and slice
    games_with_reviews.sort(key=lambda x: x["weighted_score"], reverse=True)
    top_games = games_with_reviews[:TOP_N_GAMES]

    # Step 5: Fetch Cover URLs for Top N
    print(f"\n🖼️  Fetching cover art for Top {TOP_N_GAMES} games...")
    for game in top_games:
        print(f"  Fetching cover for: {game['name']} (score: {game['weighted_score']:.0f})")
        cover_url = get_steamcmd_cover(game['appid'])
        game['cover_url'] = cover_url
        time.sleep(STEAMCMD_DELAY)

    # Step 6: Save to JSON
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "top_recent.json"
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(top_games, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to {output_file}")
    print(f"\nTop {TOP_N_GAMES} games by weighted score:")
    for i, game in enumerate(top_games, 1):
        print(f"  {i}. {game['name']}: {game['ratio']:.1%} ({game['total_reviews']} reviews) → score: {game['weighted_score']:.0f}")

if __name__ == "__main__":
    main()
