BASE_WHERE = (
    f"first_release_date > {thirty_days_ago} "
    f"& first_release_date <= {now} "
    f"& platforms = ({p_str}) "
    f"& themes != ({t_str}) "
    f"& genres != ({g_str}) "
    f"& category = (0, 8, 9) "
)

QUALITY_LEVELS = [
    # Level 1: very strict
    "& (follows > 15 | rating_count > 20 | aggregated_rating_count > 5) "
    "& cover != null "
    "& game_modes = (1) ",

    # Level 2: still good
    "& (follows > 8 | rating_count > 10) ",

    # Level 3: acceptable
    "& follows > 3 ",

    # Level 4: last resort (but still filtered)
    ""
]

games = []

for i, quality_filter in enumerate(QUALITY_LEVELS, start=1):
    query = (
        "fields name, first_release_date, platforms.id, platforms.name, "
        "cover.url, websites.url, websites.category, "
        "follows, rating, rating_count, aggregated_rating; "
        "where "
        + BASE_WHERE
        + quality_filter +
        "sort first_release_date desc; "
        "limit 50;"
    )

    response = requests.post(
        "https://api.igdb.com/v4/games",
        headers=headers,
        data=query,
        timeout=15,
    )

    if response.status_code != 200:
        print(response.text)
        response.raise_for_status()

    games = response.json()
    if games:
        print(f"Quality level {i} matched {len(games)} games.")
        break

if not games:
    print("No games found after all relaxations.")
