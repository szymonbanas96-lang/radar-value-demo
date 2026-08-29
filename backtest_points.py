import argparse
from pathlib import Path
import numpy as np
import pandas as pd

from points_radar import PointsRadarV1
from nba_data_service import fetch_player_game_log


def backtest_player(player: str, games: pd.DataFrame, warmup: int = 10) -> pd.DataFrame:
    games = games.copy()
    games["GAME_DATE"] = pd.to_datetime(games["GAME_DATE"])
    games = games.sort_values("GAME_DATE").reset_index(drop=True)

    radar = PointsRadarV1()
    rows = []

    for i in range(warmup, len(games)):
        target = games.iloc[i]
        # Critical anti-leak rule: history ends BEFORE the target game.
        history = games.iloc[:i].copy()

        target_is_home = "@" not in str(target["MATCHUP"])
        days_rest = None
        if i > 0:
            days_rest = max(0, (target["GAME_DATE"] - games.iloc[i-1]["GAME_DATE"]).days - 1)

        p = radar.project(
            player=player,
            history=history,
            target_is_home=target_is_home,
            opponent_def_factor=1.0,  # neutral in v1; matchup module comes after baseline validation
            days_rest=days_rest,
        )

        actual = float(target["PTS"])
        error = p.projection - actual
        rows.append({
            "player": player,
            "game_date": target["GAME_DATE"].date().isoformat(),
            "matchup": target["MATCHUP"],
            "projection": p.projection,
            "actual": actual,
            "error": round(error, 2),
            "abs_error": round(abs(error), 2),
            "model_score": p.model_score,
            "pts_l5": p.pts_l5,
            "pts_l10": p.pts_l10,
            "min_l5": p.minutes_l5,
            "min_l10": p.minutes_l10,
            "fga_l5": p.fga_l5,
        })

    return pd.DataFrame(rows)


def metrics(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    err = df["projection"] - df["actual"]
    ae = err.abs()
    return {
        "predictions": int(len(df)),
        "MAE": round(float(ae.mean()), 3),
        "RMSE": round(float(np.sqrt((err ** 2).mean())), 3),
        "BIAS": round(float(err.mean()), 3),
        "within_3_pts_pct": round(float((ae <= 3).mean() * 100), 1),
        "within_5_pts_pct": round(float((ae <= 5).mean() * 100), 1),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--player", required=True, help='e.g. "Jalen Brunson"')
    parser.add_argument("--season", default="2025-26")
    parser.add_argument("--csv", help="Optional local game-log CSV instead of NBA API")
    args = parser.parse_args()

    if args.csv:
        games = pd.read_csv(args.csv)
    else:
        print(f"Downloading {args.player} — {args.season}...")
        games = fetch_player_game_log(args.player, args.season)

    result = backtest_player(args.player, games)
    out = Path("points_backtest.csv")
    result.to_csv(out, index=False, encoding="utf-8-sig")

    print("\nPOINTS RADAR v1 — HISTORICAL BACKTEST")
    for k, v in metrics(result).items():
        print(f"{k}: {v}")
    print(f"\nSaved: {out.resolve()}")


if __name__ == "__main__":
    main()
