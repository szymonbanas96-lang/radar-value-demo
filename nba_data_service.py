import time
import pandas as pd
from nba_api.stats.endpoints import playergamelog
from nba_api.stats.static import players


def find_player_id(full_name: str) -> int:
    matches = players.find_players_by_full_name(full_name)
    if not matches:
        raise ValueError(f"NBA player not found: {full_name}")
    exact = [p for p in matches if p["full_name"].lower() == full_name.lower()]
    return int((exact or matches)[0]["id"])


def fetch_player_game_log(
    full_name: str,
    season: str,
    season_type: str = "Regular Season",
    retries: int = 3,
) -> pd.DataFrame:
    player_id = find_player_id(full_name)
    last_error = None

    for attempt in range(retries):
        try:
            df = playergamelog.PlayerGameLog(
                player_id=player_id,
                season=season,
                season_type_all_star=season_type,
                timeout=30,
            ).get_data_frames()[0]
            if df.empty:
                raise RuntimeError("NBA endpoint returned no games")
            df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
            return df.sort_values("GAME_DATE").reset_index(drop=True)
        except Exception as e:
            last_error = e
            time.sleep(1.5 * (attempt + 1))

    raise RuntimeError(f"Could not download {full_name}: {last_error}")
