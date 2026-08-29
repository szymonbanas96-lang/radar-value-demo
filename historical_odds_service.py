import os
from typing import List, Optional, Dict, Any
import requests
import pandas as pd
import time

BASE_URL = "https://api.sportsgameodds.com/v2/events"


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_historical_nba_points(
    starts_after: str,
    starts_before: str,
    api_key: Optional[str] = None,
    bookmaker_ids: Optional[List[str]] = None,
    limit: int = 50,
) -> pd.DataFrame:
    """
    Pull finalized NBA events with historical opening/closing POINTS props.
    Requires SportsGameOdds historical access (Pro+ according to provider docs).
    """
    api_key = api_key or os.getenv("SPORTSGAMEODDS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing SPORTSGAMEODDS_API_KEY")

    params: Dict[str, Any] = {
        "apiKey": api_key,
        "leagueID": "NBA",
        "finalized": "true",
        "includeOpenCloseOdds": "true",
        "startsAfter": starts_after,
        "startsBefore": starts_before,
        "limit": limit,
    }
    if bookmaker_ids:
        params["bookmakerID"] = ",".join(bookmaker_ids)

    rows = []
    cursor = None

    while True:
        p = dict(params)
        if cursor:
            p["cursor"] = cursor

        max_retries = 8
        for attempt in range(max_retries):
            r = requests.get(BASE_URL, params=p, timeout=30)

            if r.status_code == 429:
                retry_after = r.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else min(60, 5 * (attempt + 1))
                except Exception:
                    wait = min(60, 5 * (attempt + 1))
                print(f"Rate limit 429 — waiting {wait:.0f}s before retry {attempt+1}/{max_retries}...")
                time.sleep(wait)
                continue

            r.raise_for_status()
            break
        else:
            raise RuntimeError("SportsGameOdds rate limit persisted after retries.")

        payload = r.json()
        events = payload.get("data") or []
        print(f"Historical odds page: {len(events)} events")

        for event in events:
            event_id = event.get("eventID")
            teams = event.get("teams") or {}
            away = (((teams.get("away") or {}).get("names") or {}).get("long")) or "Away"
            home = (((teams.get("home") or {}).get("names") or {}).get("long")) or "Home"
            game = f"{away} @ {home}"
            start_time = event.get("startsAt") or event.get("startTime")

            for odd_id, market in (event.get("odds") or {}).items():
                if (market.get("statID") or "").lower() != "points":
                    continue
                if market.get("periodID") != "game" or market.get("betTypeID") != "ou":
                    continue
                if (market.get("sideID") or "").lower() != "over":
                    continue

                player_id = market.get("playerID") or market.get("statEntityID")
                if not player_id or player_id in {"all", "home", "away"}:
                    continue

                market_name = (market.get("marketName") or "").strip()
                player = market_name
                suffix = " Points Over/Under"
                if market_name.lower().endswith(suffix.lower()):
                    player = market_name[:-len(suffix)].strip()

                for book, info in (market.get("byBookmaker") or {}).items():
                    open_line = _to_float(info.get("openOverUnder"))
                    close_line = _to_float(info.get("closeOverUnder"))
                    if open_line is None and close_line is None:
                        continue

                    rows.append({
                        "event_id": event_id,
                        "game": game,
                        "start_time": start_time,
                        "player": player,
                        "player_id": player_id,
                        "bookmaker": book,
                        "open_line": open_line,
                        "close_line": close_line,
                        "open_odds": info.get("openOdds"),
                        "close_odds": info.get("closeOdds"),
                        "odd_id": market.get("oddID") or odd_id,
                        "actual_points": _to_float(market.get("score")),
                    })

        cursor = payload.get("nextCursor")
        if not cursor:
            break

    return pd.DataFrame(rows)
