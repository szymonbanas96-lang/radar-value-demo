from dataclasses import dataclass, asdict
import pandas as pd


@dataclass
class OpportunitySignal:
    score: int
    flagged: bool
    missing_count: int
    missing_names: str
    missing_impact: float
    baseline_minutes: float
    last_minutes: float
    minutes_boost: float
    baseline_fga: float
    last_fga: float
    fga_boost: float
    projected_minutes_boost: float
    projection_adjustment: float

    def to_dict(self):
        return asdict(self)


def _num(s):
    return pd.to_numeric(s, errors="coerce")


def opportunity_signal(player_games: pd.DataFrame, team_id: int, player_id: int, target_date) -> OpportunitySignal:
    """
    Leak-safe role/opportunity proxy. It only uses rows BEFORE target_date.

    Logic:
    1) Identify important teammates from games before the team's most recent game.
    2) Check whether those teammates missed the most recent team game.
    3) Check whether the candidate gained minutes / FGA in that same most recent game.

    This is NOT an injury feed. A missing teammate may have been injured, rested,
    traded or DNP. The purpose is to test whether a visible rotation change tends
    to persist into the next game.
    """
    d = pd.Timestamp(target_date)
    prior_team = player_games[(player_games["TEAM_ID"] == team_id) & (player_games["GAME_DATE"] < d)].copy()
    dates = sorted(prior_team["GAME_DATE"].drop_duplicates(), reverse=True)
    if len(dates) < 7:
        return OpportunitySignal(0, False, 0, "", 0.0, 0, 0, 0, 0, 0, 0, 0, 0)

    last_team_date = dates[0]
    training_dates = dates[1:11]
    train = prior_team[prior_team["GAME_DATE"].isin(training_dates)].copy()
    last_game = prior_team[prior_team["GAME_DATE"] == last_team_date].copy()

    # Important teammates, learned BEFORE the most recent team game.
    agg = train.groupby(["PLAYER_ID", "PLAYER_NAME"], as_index=False).agg(
        games=("GAME_ID", "nunique"), avg_min=("MIN", "mean"), avg_pts=("PTS", "mean")
    )
    important = agg[(agg["games"] >= 4) & (agg["avg_min"] >= 24) & (agg["avg_pts"] >= 10)].copy()
    important = important[important["PLAYER_ID"] != player_id]
    appeared = set(last_game["PLAYER_ID"].tolist())
    missing = important[~important["PLAYER_ID"].isin(appeared)].copy()
    if len(missing):
        missing["impact"] = (missing["avg_min"] / 36.0) + (missing["avg_pts"] / 22.0)
        missing_impact = min(3.0, float(missing["impact"].sum()))
        missing_names = ", ".join(missing.sort_values("impact", ascending=False)["PLAYER_NAME"].head(4).tolist())
    else:
        missing_impact, missing_names = 0.0, ""

    # Candidate's normal role BEFORE the most recent game.
    hist = train[train["PLAYER_ID"] == player_id].sort_values("GAME_DATE")
    cand_last = last_game[last_game["PLAYER_ID"] == player_id]
    if len(hist) < 4 or cand_last.empty:
        return OpportunitySignal(0, False, len(missing), missing_names, round(missing_impact, 2), 0, 0, 0, 0, 0, 0, 0, 0)

    baseline_min = float(_num(hist["MIN"]).mean())
    baseline_fga = float(_num(hist["FGA"]).mean())
    last_min = float(_num(cand_last["MIN"]).iloc[0])
    last_fga = float(_num(cand_last["FGA"]).iloc[0])
    min_boost = last_min - baseline_min
    fga_boost = last_fga - baseline_fga

    # Radar Value's target niche: secondary/bench players whose role expands.
    role_band = 1.0 if 8 <= baseline_min <= 28 else (0.45 if baseline_min < 8 else 0.25)
    score = (
        24 * min(1.0, missing_impact / 1.5)
        + 44 * min(1.0, max(0.0, min_boost) / 10.0)
        + 22 * min(1.0, max(0.0, fga_boost) / 5.0)
        + 10 * role_band
    )
    score = int(max(0, min(100, round(score))))

    # Require both a missing important teammate AND visible role confirmation.
    flagged = bool(missing_impact > 0 and baseline_min <= 28 and min_boost >= 4 and score >= 50)

    # Persistence assumption is conservative: retain only part of last game's jump.
    predicted_min_boost = max(0.0, min(10.0, min_boost * 0.55)) if flagged else 0.0
    # Approximate points/min from prior role, capped to avoid tiny-minute explosions.
    hist_pts = float(_num(hist["PTS"]).mean())
    ppm = max(0.20, min(0.85, hist_pts / baseline_min)) if baseline_min > 0 else 0.45
    min_adj = predicted_min_boost * ppm
    shot_adj = max(0.0, min(1.4, fga_boost * 0.16)) if flagged else 0.0
    projection_adjustment = min(4.5, min_adj * 0.65 + shot_adj)

    return OpportunitySignal(
        score=score, flagged=flagged, missing_count=int(len(missing)), missing_names=missing_names,
        missing_impact=round(missing_impact, 2), baseline_minutes=round(baseline_min, 1),
        last_minutes=round(last_min, 1), minutes_boost=round(min_boost, 1),
        baseline_fga=round(baseline_fga, 1), last_fga=round(last_fga, 1), fga_boost=round(fga_boost, 1),
        projected_minutes_boost=round(predicted_min_boost, 1), projection_adjustment=round(projection_adjustment, 2)
    )
