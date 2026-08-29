import os
from typing import Dict, List, Optional

import pandas as pd
import requests

BASE_URL = "https://api.sportsgameodds.com/v2/events"

# We only want the three core full-game O/U player markets for now.
ALLOWED_STATS = {
    "points": "PTS",
    "assists": "AST",
    "rebounds": "REB",
}

TEAM_ENTITY_IDS = {"all", "home", "away"}


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _event_name(event: dict) -> str:
    teams = event.get("teams") or {}
    away = (((teams.get("away") or {}).get("names") or {}).get("long")) or "Away"
    home = (((teams.get("home") or {}).get("names") or {}).get("long")) or "Home"
    return f"{away} @ {home}"


def _player_name_from_market(market: dict) -> str:
    # marketName is currently the most convenient readable field in the API,
    # e.g. "LeBron James Points Over/Under".
    market_name = (market.get("marketName") or "").strip()
    stat_id = (market.get("statID") or "").strip().lower()

    if market_name:
        suffixes = {
            "points": " Points Over/Under",
            "assists": " Assists Over/Under",
            "rebounds": " Rebounds Over/Under",
        }
        suffix = suffixes.get(stat_id, "")
        if suffix and market_name.lower().endswith(suffix.lower()):
            return market_name[:-len(suffix)].strip()

    # Stable fallback if readable metadata changes.
    player_id = market.get("playerID") or market.get("statEntityID") or ""
    return player_id.replace("_NBA", "").replace("_", " ").title()


def fetch_nba_player_props(
    api_key: Optional[str] = None,
    bookmaker_ids: Optional[List[str]] = None,
    limit: int = 50,
    include_alt_lines: bool = False,
) -> pd.DataFrame:
    """
    Fetch current NBA full-game player prop lines for:
    - points
    - assists
    - rebounds

    Returns one row per sportsbook/side/market.
    API key can be passed directly or stored as SPORTSGAMEODDS_API_KEY.
    """
    api_key = api_key or os.getenv("SPORTSGAMEODDS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing SportsGameOdds API key. "
            "Set SPORTSGAMEODDS_API_KEY in the environment or pass api_key=..."
        )

    params = {
        "apiKey": api_key,
        "leagueID": "NBA",
        "oddsAvailable": "true",
        "includeAltLines": str(include_alt_lines).lower(),
        "limit": limit,
    }
    if bookmaker_ids:
        params["bookmakerID"] = ",".join(bookmaker_ids)

    response = requests.get(BASE_URL, params=params, timeout=20)
    response.raise_for_status()
    payload = response.json()

    events = payload.get("data")
    if events is None:
        # Defensive fallback for possible response wrappers.
        events = payload.get("events", [])

    rows: List[Dict] = []

    for event in events or []:
        game = _event_name(event)
        event_id = event.get("eventID")
        start_time = (
            event.get("startsAt")
            or event.get("startTime")
            or event.get("scheduledStart")
            or event.get("status", {}).get("startsAt")
        )

        odds = event.get("odds") or {}

        for odd_id, market in odds.items():
            stat_id = (market.get("statID") or "").lower()
            if stat_id not in ALLOWED_STATS:
                continue

            if market.get("periodID") != "game":
                continue
            if market.get("betTypeID") != "ou":
                continue

            entity_id = market.get("statEntityID")
            if not entity_id or entity_id in TEAM_ENTITY_IDS:
                continue

            side = (market.get("sideID") or "").lower()
            if side not in {"over", "under"}:
                continue

            player = _player_name_from_market(market)
            books = market.get("byBookmaker") or {}

            # Keep each book separately. Radar can later choose consensus,
            # best line, or a specific bookmaker without losing information.
            for bookmaker, book in books.items():
                if not book.get("available", False):
                    continue

                line = _to_float(book.get("overUnder"))
                if line is None:
                    continue

                rows.append({
                    "event_id": event_id,
                    "game": game,
                    "start_time": start_time,
                    "player": player,
                    "player_id": market.get("playerID") or entity_id,
                    "market": ALLOWED_STATS[stat_id],
                    "stat_id": stat_id,
                    "side": side.upper(),
                    "bookmaker": bookmaker,
                    "line": line,
                    "odds": book.get("odds"),
                    "last_updated": book.get("lastUpdatedAt"),
                    "odd_id": market.get("oddID") or odd_id,
                    "fair_line": _to_float(market.get("fairOverUnder")),
                    "consensus_book_line": _to_float(market.get("bookOverUnder")),
                })

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=[
            "event_id", "game", "start_time", "player", "player_id",
            "market", "stat_id", "side", "bookmaker", "line", "odds",
            "last_updated", "odd_id", "fair_line", "consensus_book_line"
        ])

    return df.sort_values(
        ["game", "player", "market", "bookmaker", "side"]
    ).reset_index(drop=True)


def build_consensus_lines(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produces one consensus row per player + market + game.
    Uses the median sportsbook line from OVER rows to avoid counting
    the same O/U line twice.
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "event_id", "game", "start_time", "player", "player_id",
            "market", "consensus_line", "books", "latest_update"
        ])

    over = df[df["side"] == "OVER"].copy()
    if over.empty:
        over = df.copy()

    result = (
        over.groupby(
            ["event_id", "game", "start_time", "player", "player_id", "market"],
            dropna=False,
            as_index=False,
        )
        .agg(
            consensus_line=("line", "median"),
            books=("bookmaker", "nunique"),
            latest_update=("last_updated", "max"),
        )
    )
    return result.sort_values(
        ["game", "market", "player"]
    ).reset_index(drop=True)


if __name__ == "__main__":
    props = fetch_nba_player_props()
    consensus = build_consensus_lines(props)

    print("\n=== RAW BOOKMAKER LINES ===")
    if props.empty:
        print("No NBA PTS/AST/REB props are currently available.")
    else:
        print(props[[
            "game", "player", "market", "side", "bookmaker", "line", "odds"
        ]].to_string(index=False))

    print("\n=== CONSENSUS LINES ===")
    if consensus.empty:
        print("No consensus lines available.")
    else:
        print(consensus[[
            "game", "player", "market", "consensus_line", "books"
        ]].to_string(index=False))

    props.to_csv("nba_props_raw.csv", index=False, encoding="utf-8-sig")
    consensus.to_csv("nba_props_consensus.csv", index=False, encoding="utf-8-sig")
    print("\nSaved: nba_props_raw.csv, nba_props_consensus.csv")
