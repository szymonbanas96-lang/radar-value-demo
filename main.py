import pandas as pd
import os
from datetime import datetime
from nba_api.stats.endpoints import scoreboardv2, leaguegamefinder, boxscoretraditionalv2
from nba_api.stats.static.players import find_players_by_full_name


def get_players_from_last_game(game_id, min_minutes=10):
    boxscore = boxscoretraditionalv2.BoxScoreTraditionalV2(
        game_id=game_id,
        timeout=60
    )

    players_df = boxscore.player_stats.get_data_frame()
    players_df = players_df[players_df["MIN"].notna()].copy()

    players_df["MIN_FLOAT"] = (
        players_df["MIN"]
        .str.split(":")
        .str[0]
        .astype(float)
    )

    players_df = players_df[players_df["MIN_FLOAT"] >= min_minutes]

    return players_df["PLAYER_NAME"].tolist()


def get_today_games(game_date):
    scoreboard = scoreboardv2.ScoreboardV2(
        game_date=game_date,
        timeout=60
    )

    return scoreboard.game_header.get_data_frame()


def get_players_from_games(game_ids, min_minutes=10):
    all_players = []

    for game_id in game_ids:
        try:
            players = get_players_from_last_game(
                game_id=game_id,
                min_minutes=min_minutes
            )

            all_players.extend(players)

        except Exception as e:
            print(f"Błąd pobierania zawodników z meczu {game_id}: {e}")

    return list(dict.fromkeys(all_players))


# DATA MECZÓW DO ANALIZY
target_date = "05/25/2026"

games_today = get_today_games(target_date)

if games_today.empty:
    print("Nie znaleziono meczów dla tej daty.")
    exit()

today_game_ids = games_today["GAME_ID"].tolist()

print("GAME IDs DO ANALIZY:")
print(today_game_ids)

players_to_check = get_players_from_games(
    game_ids=today_game_ids,
    min_minutes=10
)

print("\nZAWODNICY DO ANALIZY:")
print(players_to_check)


book_df = pd.read_csv("book_lines.csv")
book_lines = dict(zip(book_df["player"], book_df["book_line"]))

matchup_df = pd.read_csv("matchup_boosts.csv")
matchup_boosts = dict(zip(matchup_df["player"], matchup_df["boost"]))

injury_df = pd.read_csv("injury_boosts.csv")
injury_boosts = dict(zip(injury_df["player"], injury_df["boost"]))
injury_reasons = dict(zip(injury_df["player"], injury_df["reason"]))

team_df = pd.read_csv("team_defense.csv")
team_boosts = dict(zip(team_df["team"], team_df["boost"]))

print("\nPOBIERANIE DANYCH...\n")

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

print("MECZE DO ANALIZY:\n")

for index, row in games_today.iterrows():
    print(f"{row['GAME_ID']} | {row['GAME_STATUS_TEXT']}")

print("\nDAILY RADAR SCANNER:\n")

radar_results = []

for player_name in players_to_check:
    try:
        players = find_players_by_full_name(player_name)

        if not players:
            print(f"{player_name} | nie znaleziono")
            continue

        selected_player = players[0]
        player_id = selected_player["id"]
        full_name = selected_player["full_name"]

        book_line = book_lines.get(full_name)

        if book_line is None:
            print(f"{full_name} | brak linii w book_lines.csv")
            continue

        matchup_boost = matchup_boosts.get(full_name, 0)
        injury_boost = injury_boosts.get(full_name, 0)
        injury_reason = injury_reasons.get(full_name, "")

        games = leaguegamefinder.LeagueGameFinder(
            player_id_nullable=player_id,
            timeout=60
        )

        games_df = games.get_data_frames()[0]

        last_5 = games_df.head(5).copy()
        last_10 = games_df.head(10).copy()

        if last_5.empty or last_10.empty:
            print(f"{full_name} | brak danych meczowych")
            continue

        latest_matchup = last_5.iloc[0]["MATCHUP"]

        last_5["PRA"] = last_5["PTS"] + last_5["REB"] + last_5["AST"]

        avg_pra_5 = last_5["PRA"].mean()
        avg_pra_10 = (
            last_10["PTS"].mean()
            + last_10["REB"].mean()
            + last_10["AST"].mean()
        )

        avg_min_5 = last_5["MIN"].mean()
        avg_min_10 = last_10["MIN"].mean()
        minutes_trend = avg_min_5 - avg_min_10

        team_boost = 0

        for team_name, boost in team_boosts.items():
            if team_name in latest_matchup:
                team_boost = boost

        real_edge = avg_pra_5 - book_line
        covers = (last_5["PRA"] > book_line).sum()

        score = avg_pra_5
        score += minutes_trend * 2
        score += avg_pra_5 - avg_pra_10
        score += real_edge * 3
        score += covers * 2
        score += matchup_boost
        score += injury_boost
        score += team_boost

        elite_play = (
            score >= 45
            and real_edge >= 3
            and covers >= 4
        )

        if score >= 45:
            signal = "🔥 STRONG OVER TREND"
        elif score >= 35:
            signal = "⚠️ OVER TREND"
        elif score <= 15:
            signal = "🔻 COLD TREND"
        else:
            signal = "➖ NEUTRAL"

        radar_results.append({
            "timestamp": timestamp,
            "name": full_name,
            "score": round(score, 1),
            "signal": signal,
            "pra5": round(avg_pra_5, 1),
            "pra10": round(avg_pra_10, 1),
            "minutes_trend": round(minutes_trend, 1),
            "edge": round(avg_pra_5 - avg_pra_10, 1),
            "book_line": book_line,
            "real_edge": round(real_edge, 1),
            "covers": int(covers),
            "matchup_boost": matchup_boost,
            "injury_boost": injury_boost,
            "injury_reason": injury_reason,
            "team_boost": team_boost,
            "elite_play": elite_play,
        })

    except Exception as e:
        print(f"Błąd dla {player_name}: {e}")

print("\nTOP RADAR VALUE PICKS:\n")

sorted_results = sorted(
    radar_results,
    key=lambda x: x["score"],
    reverse=True
)

for player in sorted_results:
    print(
        f"{player['signal']} | "
        f"{player['name']} | "
        f"Radar Score: {player['score']} | "
        f"EDGE: {player['edge']} | "
        f"PRA5: {player['pra5']} | "
        f"PRA10: {player['pra10']} | "
        f"MIN trend: {player['minutes_trend']} | "
        f"BOOK: {player['book_line']} | "
        f"REAL EDGE: {player['real_edge']} | "
        f"COVERS: {player['covers']}/5"
    )

df_results = pd.DataFrame(sorted_results)

df_results.to_csv(
    "radar_results.csv",
    index=False,
    encoding="utf-8-sig"
)

history_file = "history.csv"

if os.path.exists(history_file):
    old_history = pd.read_csv(history_file)
    updated_history = pd.concat(
        [old_history, df_results],
        ignore_index=True
    )
else:
    updated_history = df_results

updated_history.to_csv(
    history_file,
    index=False,
    encoding="utf-8-sig"
)

print("\nZapisano wyniki do pliku: radar_results.csv")
print("Zapisano historię do history.csv")