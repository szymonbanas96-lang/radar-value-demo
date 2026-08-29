import argparse, re, time
import numpy as np
import pandas as pd
from nba_api.stats.endpoints import leaguegamelog

from points_radar_v2 import PointsRadarV2
from historical_team_context import fetch_league_team_games, add_opponent_rows, historical_context
from role_opportunity import opportunity_signal


def fetch_league_player_games(season, retries=3):
    last = None
    for attempt in range(retries):
        try:
            df = leaguegamelog.LeagueGameLog(
                counter=0, direction="ASC", league_id="00", player_or_team_abbreviation="P",
                season=season, season_type_all_star="Regular Season", sorter="DATE", timeout=45,
            ).get_data_frames()[0]
            df["GAME_DATE"] = pd.to_datetime(df["GAME_DATE"])
            return df.sort_values(["GAME_DATE", "GAME_ID", "PLAYER_ID"]).reset_index(drop=True)
        except Exception as e:
            last = e; time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Could not download league player logs: {last}")


def parse_matchup(matchup):
    m = re.match(r"([A-Z]{2,3})\s+(?:vs\.|@)\s+([A-Z]{2,3})", str(matchup))
    return (m.group(1), m.group(2)) if m else (None, None)


def metric(df, col):
    e = df[col] - df["actual"]
    ae = e.abs()
    return {
        "N": len(df), "MAE": round(float(ae.mean()), 3),
        "RMSE": round(float(np.sqrt((e**2).mean())), 3),
        "BIAS": round(float(e.mean()), 3),
        "within3": round(float((ae <= 3).mean()*100), 1),
        "within5": round(float((ae <= 5).mean()*100), 1),
    }


def main():
    ap = argparse.ArgumentParser(description="Radar Value Points v2.4 Role Opportunity historical experiment")
    ap.add_argument("--season", default="2025-26")
    ap.add_argument("--min-score", type=int, default=50)
    ap.add_argument("--max-baseline-min", type=float, default=28)
    ap.add_argument("--limit", type=int, default=0, help="Optional max flagged rows for quick debugging; 0 = all")
    args = ap.parse_args()

    print("Downloading league-wide PLAYER game logs...")
    pg = fetch_league_player_games(args.season)
    print("Player-game rows:", len(pg))
    print("Downloading league-wide TEAM context...")
    tg = fetch_league_team_games(args.season)
    prepared = add_opponent_rows(tg)
    print("Team-game rows:", len(tg))

    model = PointsRadarV2()
    rows = []
    targets = pg.sort_values("GAME_DATE").reset_index(drop=True)

    # Start after enough season history exists; individual player still needs >=10 games.
    season_start = targets["GAME_DATE"].min()
    targets = targets[targets["GAME_DATE"] >= season_start + pd.Timedelta(days=25)]

    total = len(targets)
    for idx, (_, t) in enumerate(targets.iterrows(), 1):
        pid = int(t["PLAYER_ID"]); team_id = int(t["TEAM_ID"]); date = t["GAME_DATE"]
        sig = opportunity_signal(pg, team_id, pid, date)
        if not sig.flagged or sig.score < args.min_score or sig.baseline_minutes > args.max_baseline_min:
            continue

        hist = pg[(pg["PLAYER_ID"] == pid) & (pg["GAME_DATE"] < date)].copy()
        if len(hist) < 10:
            continue
        # PointsRadar uses most recent history; cap at 40 for speed/cleanliness.
        hist = hist.sort_values("GAME_DATE").tail(40)
        matchup = str(t["MATCHUP"])
        own, opp = parse_matchup(matchup)
        home = "@" not in matchup
        prev_date = hist["GAME_DATE"].max()
        rest = max(0, (date - prev_date).days - 1)
        defense_factor, pace_factor = (1.0, 1.0)
        if own and opp:
            defense_factor, pace_factor = historical_context(prepared, opp, own, date, lookback=15)

        try:
            p = model.project(
                str(t["PLAYER_NAME"]), hist, target_is_home=home,
                opponent_points_factor=defense_factor, pace_factor=pace_factor, days_rest=rest
            )
        except Exception:
            continue

        v21 = float(p.projection)
        v24 = round(max(0.0, v21 + sig.projection_adjustment), 1)
        actual = float(t["PTS"])
        target_min = float(t["MIN"])
        actual_min_change = target_min - sig.baseline_minutes
        actual_pts_lift = actual - float(p.pts_l10)

        rows.append({
            "player": t["PLAYER_NAME"], "game_date": date.date().isoformat(), "matchup": matchup,
            "opportunity_score": sig.score, "missing_teammates": sig.missing_names,
            "missing_count": sig.missing_count, "missing_impact": sig.missing_impact,
            "baseline_minutes": sig.baseline_minutes, "last_minutes": sig.last_minutes,
            "pregame_minutes_boost": sig.minutes_boost, "target_minutes": round(target_min,1),
            "actual_minutes_change": round(actual_min_change,1),
            "baseline_fga": sig.baseline_fga, "last_fga": sig.last_fga, "pregame_fga_boost": sig.fga_boost,
            "v21_projection": v21, "v24_projection": v24, "opportunity_adjustment": sig.projection_adjustment,
            "actual": actual, "actual_pts_vs_l10": round(actual_pts_lift,1),
            "v21_abs_error": round(abs(v21-actual),1), "v24_abs_error": round(abs(v24-actual),1),
        })
        if len(rows) % 100 == 0:
            print(f"Flagged rows processed: {len(rows)}")
        if args.limit and len(rows) >= args.limit:
            break

    if not rows:
        print("No flagged Role Opportunity rows found.")
        return

    df = pd.DataFrame(rows).sort_values(["game_date", "opportunity_score"], ascending=[True, False])
    m21, m24 = metric(df, "v21_projection"), metric(df, "v24_projection")

    print("\n" + "="*78)
    print("ROLE OPPORTUNITY SUBSET — PRE-GAME, LEAK-SAFE PROXY")
    print("="*78)
    print("V2.1:", m21)
    print("V2.4 ROLE OPPORTUNITY:", m24)
    print(f"MAE CHANGE: {m24['MAE']-m21['MAE']:+.3f}")
    print(f"MAE IMPROVEMENT: {(m21['MAE']-m24['MAE'])/m21['MAE']*100:.2f}%")
    print(f"Average actual minute change vs normal role: {df['actual_minutes_change'].mean():+.2f}")
    print(f"Pct target games with >= +5 actual minutes: {(df['actual_minutes_change'] >= 5).mean()*100:.1f}%")
    print(f"Pct target games scoring above prior L10: {(df['actual_pts_vs_l10'] > 0).mean()*100:.1f}%")

    # Score bands tell us whether higher Opportunity Score really means stronger persistence.
    bins = [49, 59, 69, 79, 89, 100]
    labels = ["50-59", "60-69", "70-79", "80-89", "90-100"]
    df["score_band"] = pd.cut(df["opportunity_score"], bins=bins, labels=labels, include_lowest=True)
    band_rows = []
    for band, g in df.groupby("score_band", observed=True):
        band_rows.append({
            "score_band": str(band), "N": len(g),
            "avg_actual_min_change": round(float(g["actual_minutes_change"].mean()),2),
            "pct_plus5_minutes": round(float((g["actual_minutes_change"]>=5).mean()*100),1),
            "pct_scored_above_l10": round(float((g["actual_pts_vs_l10"]>0).mean()*100),1),
            "v21_MAE": metric(g,"v21_projection")["MAE"], "v24_MAE": metric(g,"v24_projection")["MAE"],
        })
    bands = pd.DataFrame(band_rows)
    if len(bands):
        print("\nOPPORTUNITY SCORE BANDS")
        print(bands.to_string(index=False))

    df.to_csv("points_v24_role_opportunity_rows.csv", index=False, encoding="utf-8-sig")
    bands.to_csv("points_v24_opportunity_bands.csv", index=False, encoding="utf-8-sig")
    print("\nSaved: points_v24_role_opportunity_rows.csv")
    print("Saved: points_v24_opportunity_bands.csv")
    print("\nIMPORTANT: this experiment detects a prior-game rotation shift, not an official injury status.")

if __name__ == "__main__":
    main()
