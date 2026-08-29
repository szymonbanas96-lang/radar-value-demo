import argparse
import os
import re
import time
from pathlib import Path
import numpy as np
import pandas as pd

from nba_data_service import fetch_player_game_log
from points_radar_v2 import PointsRadarV2
from historical_team_context import fetch_league_team_games, add_opponent_rows, historical_context
from historical_odds_service import fetch_historical_nba_points

PLAYERS = [x.strip() for x in Path("players.txt").read_text(encoding="utf-8").splitlines() if x.strip()]


def parse_matchup(s):
    m = re.match(r"([A-Z]{2,3})\s+(?:vs\.|@)\s+([A-Z]{2,3})", str(s))
    return (m.group(1), m.group(2)) if m else (None, None)


def build_projections(season, prepared):
    model = PointsRadarV2()
    rows = []

    for n, player in enumerate(PLAYERS, 1):
        print(f"[projection {n}/{len(PLAYERS)}] {player}")
        try:
            g = fetch_player_game_log(player, season)
            g["GAME_DATE"] = pd.to_datetime(g["GAME_DATE"])
            g = g.sort_values("GAME_DATE").reset_index(drop=True)

            for i in range(20, len(g)):
                t = g.iloc[i]
                hist = g.iloc[:i].copy()
                own, opp = parse_matchup(t.MATCHUP)
                if not own or not opp:
                    continue

                dfac, pfac = historical_context(prepared, opp, own, t.GAME_DATE, 15)
                home = "@" not in str(t.MATCHUP)
                rest = max(0, (t.GAME_DATE - g.iloc[i-1].GAME_DATE).days - 1)

                p = model.project(player, hist, home, dfac, pfac, rest)
                rows.append({
                    "player": player,
                    "game_date": t.GAME_DATE.date().isoformat(),
                    "projection": p.projection,
                    "actual": float(t.PTS),
                })
        except Exception as e:
            print("  FAILED:", e)
        time.sleep(0.5)

    return pd.DataFrame(rows)


def normalize_name(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def grade(actual, line, side):
    if actual == line:
        return "PUSH"
    if side == "OVER":
        return "WIN" if actual > line else "LOSS"
    return "WIN" if actual < line else "LOSS"


def summarize(df, label):
    print("\n" + "="*72)
    print(label)
    print("="*72)
    if df.empty:
        print("No rows.")
        return

    graded = df[df.result != "PUSH"].copy()
    wins = int((graded.result == "WIN").sum())
    n = len(graded)
    wr = wins / n * 100 if n else 0
    print(f"Bets: {n}")
    print(f"Wins: {wins}")
    print(f"Win rate: {wr:.2f}%")
    print(f"Pushes: {(df.result == 'PUSH').sum()}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", default="2025-26")
    ap.add_argument("--starts-after", required=True, help="ISO date/time, e.g. 2025-10-20T00:00:00Z")
    ap.add_argument("--starts-before", required=True, help="ISO date/time")
    ap.add_argument("--bookmaker", default=None, help="Optional exact bookmaker id")
    ap.add_argument("--line-type", choices=["open","close"], default="close")
    args = ap.parse_args()

    print("Downloading historical team context...")
    prepared = add_opponent_rows(fetch_league_team_games(args.season))

    cache_file = Path(f"points_projections_{args.season}.csv")
    if cache_file.exists():
        print(f"Loading cached Points Radar projections from {cache_file}...")
        projections = pd.read_csv(cache_file)
    else:
        print("Building leak-safe Points Radar v2.1 projections...")
        projections = build_projections(args.season, prepared)
        projections.to_csv(cache_file, index=False, encoding="utf-8-sig")
        print(f"Saved projection cache: {cache_file}")

    projections["name_key"] = projections.player.map(normalize_name)

    print("Downloading historical sportsbook POINTS lines...")
    books = [args.bookmaker] if args.bookmaker else None
    odds = fetch_historical_nba_points(
        args.starts_after, args.starts_before,
        bookmaker_ids=books
    )
    if odds.empty:
        print("No historical point props returned. Check plan/date/bookmaker coverage.")
        return

    odds["name_key"] = odds.player.map(normalize_name)

    # Sportsbook timestamps are UTC; NBA GAME_DATE is tied to the US game date.
    start_utc = pd.to_datetime(odds.start_time, utc=True, errors="coerce")
    odds["game_date"] = start_utc.dt.tz_convert("America/New_York").dt.date.astype(str)

    line_col = "close_line" if args.line_type == "close" else "open_line"
    odds = odds[odds[line_col].notna()].copy()

    print(f"Historical POINTS rows returned: {len(odds)}")
    print(f"Unique sportsbook players: {odds['name_key'].nunique()}")
    print(f"Projection rows: {len(projections)}")
    print(f"Unique projection players: {projections['name_key'].nunique()}")

    common_names = set(projections["name_key"]) & set(odds["name_key"])
    print(f"Exact normalized player-name matches: {len(common_names)} / {projections['name_key'].nunique()}")

    merged = projections.merge(
        odds[["name_key","game_date","bookmaker",line_col,"open_line","close_line","actual_points"]],
        on=["name_key","game_date"], how="inner"
    )

    if merged.empty and common_names:
        print("Exact date join returned 0 rows. Trying same-player ±1 day fallback...")
        proj2 = projections.copy()
        odds2 = odds.copy()
        proj2["_pdate"] = pd.to_datetime(proj2["game_date"])
        odds2["_odate"] = pd.to_datetime(odds2["game_date"])

        candidates = proj2.merge(
            odds2[["name_key","_odate","bookmaker",line_col,"open_line","close_line","actual_points"]],
            on="name_key", how="inner"
        )
        candidates["_date_diff"] = (candidates["_pdate"] - candidates["_odate"]).abs().dt.days
        merged = candidates[candidates["_date_diff"] <= 1].copy()
        if not merged.empty:
            merged["game_date"] = merged["_pdate"].dt.date.astype(str)
            merged = merged.drop(columns=["_pdate","_odate","_date_diff"])

    if merged.empty:
        print("\nNO MATCHES — DIAGNOSTICS")
        print("="*72)
        print("Sample projection players:")
        print(projections[["player","game_date"]].head(12).to_string(index=False))
        print("\nSample sportsbook players:")
        print(odds[["player","game_date","bookmaker",line_col]].head(20).to_string(index=False))
        print("\nMost likely causes: date coverage, naming differences, or historical prop access.")
        return

    merged["line"] = merged[line_col]
    merged["edge"] = merged.projection - merged.line
    merged["side"] = np.where(merged.edge >= 0, "OVER", "UNDER")
    merged["abs_edge"] = merged.edge.abs()
    merged["result"] = merged.apply(lambda r: grade(r.actual, r.line, r.side), axis=1)

    # Buckets for the actual Radar Value thesis.
    bins = [0,1,2,3,4,999]
    labels = ["0-1","1-2","2-3","3-4","4+"]
    merged["edge_bucket"] = pd.cut(
        merged.abs_edge, bins=bins, labels=labels,
        right=False, include_lowest=True
    )

    print("\nMATCHED ROWS:", len(merged))
    print("BOOKMAKERS:", merged.bookmaker.nunique())

    summarize(merged, "ALL EDGES")

    print("\nEDGE BUCKET RESULTS")
    print("="*72)
    rows=[]
    for bucket in labels:
        x = merged[merged.edge_bucket == bucket].copy()
        graded = x[x.result != "PUSH"]
        n=len(graded)
        wr=(graded.result.eq("WIN").mean()*100) if n else np.nan
        rows.append({
            "edge_bucket": bucket,
            "bets": n,
            "win_rate": round(float(wr),2) if n else np.nan,
            "avg_abs_edge": round(float(x.abs_edge.mean()),2) if len(x) else np.nan,
        })
    bucket_df=pd.DataFrame(rows)
    print(bucket_df.to_string(index=False))

    print("\nTHRESHOLD RESULTS")
    print("="*72)
    threshold_rows=[]
    for threshold in [1,1.5,2,2.5,3,3.5,4,5]:
        x=merged[merged.abs_edge>=threshold]
        graded=x[x.result!="PUSH"]
        n=len(graded)
        wr=(graded.result.eq("WIN").mean()*100) if n else np.nan
        threshold_rows.append({
            "min_edge":threshold,
            "bets":n,
            "win_rate":round(float(wr),2) if n else np.nan
        })
    th=pd.DataFrame(threshold_rows)
    print(th.to_string(index=False))

    merged.to_csv("points_value_backtest_rows.csv", index=False, encoding="utf-8-sig")
    bucket_df.to_csv("points_value_edge_buckets.csv", index=False, encoding="utf-8-sig")
    th.to_csv("points_value_thresholds.csv", index=False, encoding="utf-8-sig")
    print("\nSaved: points_value_backtest_rows.csv, points_value_edge_buckets.csv, points_value_thresholds.csv")


if __name__ == "__main__":
    main()
