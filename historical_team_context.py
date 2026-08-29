import time
import pandas as pd
from nba_api.stats.endpoints import leaguegamelog


def fetch_league_team_games(season: str, retries: int = 3) -> pd.DataFrame:
    """
    Downloads team game logs once for the whole season.
    Historical defense/pace features are calculated only from rows BEFORE
    each target date.
    """
    last = None
    for attempt in range(retries):
        try:
            df = leaguegamelog.LeagueGameLog(
                counter=0,
                direction="DESC",
                league_id="00",
                player_or_team_abbreviation="T",
                season=season,
                season_type_all_star="Regular Season",
                sorter="DATE",
                timeout=30,
            ).get_data_frames()[0]
            df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
            return df.sort_values("GAME_DATE").reset_index(drop=True)
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Could not download league team logs: {last}")


def add_opponent_rows(team_games: pd.DataFrame) -> pd.DataFrame:
    """
    Adds opponent points by pairing the two team rows belonging to each GAME_ID.
    Also estimates possessions using the standard box-score approximation:
    FGA + 0.44*FTA - OREB + TOV.
    """
    df = team_games.copy()
    df["POSS_EST"] = (
        pd.to_numeric(df["FGA"], errors="coerce")
        + 0.44 * pd.to_numeric(df["FTA"], errors="coerce")
        - pd.to_numeric(df["OREB"], errors="coerce")
        + pd.to_numeric(df["TOV"], errors="coerce")
    )

    opp = df[["GAME_ID","TEAM_ID","PTS","POSS_EST"]].rename(columns={
        "TEAM_ID":"OPP_TEAM_ID",
        "PTS":"OPP_PTS",
        "POSS_EST":"OPP_POSS_EST",
    })
    paired = df.merge(opp, on="GAME_ID", how="left")
    paired = paired[paired["TEAM_ID"] != paired["OPP_TEAM_ID"]].copy()
    return paired


def historical_context(
    prepared: pd.DataFrame,
    opponent_abbr: str,
    player_team_abbr: str,
    target_date,
    lookback: int = 15,
):
    """
    Returns date-correct opponent defense and expected pace factors.

    Defense: opponent points allowed per estimated 100 possessions over prior games.
    Pace: average estimated possessions of both teams over prior games.

    Both are normalized against league values available BEFORE target_date.
    """
    target_date = pd.Timestamp(target_date)
    prior = prepared[prepared["GAME_DATE"] < target_date].copy()
    if prior.empty:
        return 1.0, 1.0

    opp_hist = prior[prior["TEAM_ABBREVIATION"] == opponent_abbr].tail(lookback)
    own_hist = prior[prior["TEAM_ABBREVIATION"] == player_team_abbr].tail(lookback)

    if len(opp_hist) < 5 or len(own_hist) < 5:
        return 1.0, 1.0

    # Points allowed / opponent possessions * 100.
    opp_def = (
        pd.to_numeric(opp_hist["OPP_PTS"], errors="coerce").sum()
        / pd.to_numeric(opp_hist["OPP_POSS_EST"], errors="coerce").sum()
        * 100
    )
    league_def = (
        pd.to_numeric(prior["OPP_PTS"], errors="coerce").sum()
        / pd.to_numeric(prior["OPP_POSS_EST"], errors="coerce").sum()
        * 100
    )
    defense_factor = opp_def / league_def if league_def else 1.0

    own_pace = pd.to_numeric(own_hist["POSS_EST"], errors="coerce").mean()
    opp_pace = pd.to_numeric(opp_hist["POSS_EST"], errors="coerce").mean()
    league_pace = pd.to_numeric(prior["POSS_EST"], errors="coerce").mean()
    expected_pace = (own_pace + opp_pace) / 2
    pace_factor = expected_pace / league_pace if league_pace else 1.0

    return (
        max(0.94, min(1.06, float(defense_factor))),
        max(0.96, min(1.04, float(pace_factor))),
    )
