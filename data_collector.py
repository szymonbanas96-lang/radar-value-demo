import os
import time
import pandas as pd
from nba_api.stats.endpoints import leaguegamefinder, boxscoretraditionalv2


DATABASE_FILE = "player_games.csv"

# Preseason 2026/27
SEASON = "2026-27"
SEASON_TYPE = "Pre Season"


def minutes_to_float(value):
    """
    NBA API może zwracać minuty jako:
    25
    25.0
    '25'
    '25:34'
    """
    if pd.isna(value):
        return 0.0

    try:
        if isinstance(value, (int, float)):
            return float(value)

        value = str(value)

        if ":" in value:
            minutes, seconds = value.split(":")[:2]
            return float(minutes) + float(seconds) / 60

        return float(value)

    except (ValueError, TypeError):
        return 0.0


def get_preseason_games():
    print("\n🏀 Szukam meczów preseason...")

    finder = leaguegamefinder.LeagueGameFinder(
        season_nullable=SEASON,
        season_type_nullable=SEASON_TYPE,
        league_id_nullable="00",
        timeout=60
    )

    games = finder.get_data_frames()[0]

    if games.empty:
        print("Nie znaleziono jeszcze meczów preseason.")
        return pd.DataFrame()

    # LeagueGameFinder zwraca jeden rekord na drużynę,
    # więc jeden mecz występuje dwa razy.
    games = games.drop_duplicates(subset=["GAME_ID"]).copy()

    games["GAME_DATE"] = pd.to_datetime(
        games["GAME_DATE"],
        errors="coerce"
    )

    games = games.sort_values("GAME_DATE")

    print(f"Znaleziono meczów: {len(games)}")

    return games


def get_boxscore(game_id, game_date):
    print(f"📥 Pobieram boxscore: {game_id}")

    boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(
        game_id=game_id,
        timeout=60
    )

    df = boxscore.player_stats.get_data_frame()

    if df.empty:
        print("   Brak danych.")
        return pd.DataFrame()

    # Zostawiamy tylko zawodników, którzy faktycznie zagrali.
    df = df[df["MIN"].notna()].copy()

    if df.empty:
        return pd.DataFrame()

    df["MIN"] = df["MIN"].apply(minutes_to_float)

    df = df[df["MIN"] > 0].copy()

    df["GAME_DATE"] = pd.to_datetime(game_date).strftime("%Y-%m-%d")
    df["SEASON"] = SEASON
    df["SEASON_TYPE"] = SEASON_TYPE

    wanted_columns = [
        "GAME_ID",
        "GAME_DATE",
        "SEASON",
        "SEASON_TYPE",
        "TEAM_ID",
        "TEAM_ABBREVIATION",
        "PLAYER_ID",
        "PLAYER_NAME",
        "START_POSITION",
        "MIN",
        "PTS",
        "AST",
        "REB",
        "OREB",
        "DREB",
        "FGM",
        "FGA",
        "FG_PCT",
        "FG3M",
        "FG3A",
        "FG3_PCT",
        "FTM",
        "FTA",
        "FT_PCT",
        "STL",
        "BLK",
        "TO",
        "PF",
        "PLUS_MINUS",
    ]

    # Gdyby NBA API zmieniło/ominęło którąś kolumnę,
    # collector nie wywali się od razu.
    for column in wanted_columns:
        if column not in df.columns:
            df[column] = None

    return df[wanted_columns]


def load_database():
    if not os.path.exists(DATABASE_FILE):
        return pd.DataFrame()

    try:
        return pd.read_csv(
            DATABASE_FILE,
            dtype={"GAME_ID": str}
        )

    except Exception as e:
        print(f"⚠️ Nie udało się odczytać bazy: {e}")
        return pd.DataFrame()


def save_database(df):
    df.to_csv(
        DATABASE_FILE,
        index=False,
        encoding="utf-8-sig"
    )


def main():

    print("=" * 60)
    print("🏀 RADAR VALUE — DATA COLLECTOR")
    print("=" * 60)

    games = get_preseason_games()

    if games.empty:
        return

    database = load_database()

    if not database.empty and "GAME_ID" in database.columns:
        database["GAME_ID"] = database["GAME_ID"].astype(str)
        existing_game_ids = set(database["GAME_ID"].unique())
    else:
        existing_game_ids = set()

    print(f"\nMecze już zapisane w bazie: {len(existing_game_ids)}")

    new_data = []

    for _, game in games.iterrows():

        game_id = str(game["GAME_ID"])
        game_date = game["GAME_DATE"]

        if game_id in existing_game_ids:
            print(f"✅ {game_id} już znajduje się w bazie.")
            continue

        try:
            df = get_boxscore(
                game_id=game_id,
                game_date=game_date
            )

            if not df.empty:
                new_data.append(df)

            # Nie bombardujemy NBA API requestami.
            time.sleep(1)

        except Exception as e:
            print(f"❌ Błąd dla {game_id}: {e}")

    if not new_data:
        print("\nBrak nowych danych do zapisania.")
        return

    new_df = pd.concat(
        new_data,
        ignore_index=True
    )

    if database.empty:
        updated_database = new_df

    else:
        updated_database = pd.concat(
            [database, new_df],
            ignore_index=True
        )

    # Jeden zawodnik może mieć tylko jeden rekord
    # dla danego GAME_ID.
    updated_database = updated_database.drop_duplicates(
        subset=["GAME_ID", "PLAYER_ID"],
        keep="last"
    )

    updated_database = updated_database.sort_values(
        ["GAME_DATE", "GAME_ID", "TEAM_ABBREVIATION", "PLAYER_NAME"]
    )

    save_database(updated_database)

    print("\n" + "=" * 60)
    print("✅ COLLECTOR ZAKOŃCZYŁ PRACĘ")
    print("=" * 60)

    print(f"Nowych rekordów zawodników: {len(new_df)}")
    print(f"Wszystkich rekordów w bazie: {len(updated_database)}")
    print(f"Baza: {DATABASE_FILE}")

    print("\n📊 STATYSTYKI BAZY")

    print(
        updated_database[
            ["PLAYER_NAME", "MIN", "PTS", "AST", "REB"]
        ].tail(20).to_string(index=False)
    )


if __name__ == "__main__":
    main()
