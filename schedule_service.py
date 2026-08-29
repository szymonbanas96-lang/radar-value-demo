from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests

WARSAW = ZoneInfo("Europe/Warsaw")

FALLBACK_GAMES = [
    ("2026-10-03T23:00:00Z","Miami Heat","Toronto Raptors","Videotron Centre, Quebec City","NBA Canada Game"),
    ("2026-10-05T23:00:00Z","Memphis Grizzlies","Atlanta Hawks","State Farm Arena",""),
    ("2026-10-05T23:00:00Z","Phoenix Suns","Detroit Pistons","Little Caesars Arena",""),
    ("2026-10-05T23:00:00Z","New York Knicks","Philadelphia 76ers","Xfinity Mobile Arena",""),
    ("2026-10-06T00:00:00Z","Minnesota Timberwolves","Milwaukee Bucks","Fiserv Forum",""),
    ("2026-10-06T02:00:00Z","Los Angeles Lakers","Sacramento Kings","Golden 1 Center",""),
    ("2026-10-06T23:00:00Z","Brooklyn Nets","Charlotte Hornets","Spectrum Center",""),
    ("2026-10-07T00:00:00Z","New Orleans Pelicans","Oklahoma City Thunder","BOK Center, Tulsa",""),
    ("2026-10-07T01:00:00Z","Denver Nuggets","Utah Jazz","Delta Center",""),
    ("2026-10-09T12:00:00Z","Houston Rockets","Dallas Mavericks","Venetian Arena, Macao","NBA China Game"),
    ("2026-10-10T00:00:00Z","Memphis Grizzlies","Chicago Bulls","United Center",""),
    ("2026-10-10T22:30:00Z","LA Clippers","Toronto Raptors","Rogers Arena, Vancouver","NBA Canada Game"),
    ("2026-10-10T23:00:00Z","Atlanta Hawks","Indiana Pacers","Gainbridge Fieldhouse",""),
    ("2026-10-10T23:00:00Z","Detroit Pistons","Washington Wizards","Capital One Arena",""),
    ("2026-10-11T00:00:00Z","Minnesota Timberwolves","Miami Heat","Kaseya Center",""),
    ("2026-10-11T00:00:00Z","Philadelphia 76ers","Boston Celtics","TD Garden",""),
    ("2026-10-11T00:30:00Z","Sacramento Kings","Golden State Warriors","Chase Center",""),
    ("2026-10-11T02:30:00Z","San Antonio Spurs","Phoenix Suns","Mortgage Matchup Center",""),
    ("2026-10-11T10:00:00Z","Dallas Mavericks","Houston Rockets","Venetian Arena, Macao","NBA China Game"),
    ("2026-10-13T23:00:00Z","Cleveland Cavaliers","Orlando Magic","Kia Center",""),
    ("2026-10-13T23:00:00Z","New York Knicks","Toronto Raptors","Scotiabank Arena",""),
    ("2026-10-14T00:00:00Z","Indiana Pacers","Oklahoma City Thunder","Paycom Center",""),
    ("2026-10-14T02:00:00Z","Golden State Warriors","Los Angeles Lakers","T-Mobile Arena, Las Vegas",""),
    ("2026-10-14T02:00:00Z","Portland Trail Blazers","Sacramento Kings","Golden 1 Center",""),
    ("2026-10-15T23:30:00Z","Toronto Raptors","New York Knicks","Madison Square Garden",""),
    ("2026-10-16T00:30:00Z","Oklahoma City Thunder","Houston Rockets","Toyota Center",""),
    ("2026-10-16T23:00:00Z","Boston Celtics","Philadelphia 76ers","Xfinity Mobile Arena",""),
    ("2026-10-16T23:00:00Z","Miami Heat","Orlando Magic","Kia Center",""),
    ("2026-10-16T23:00:00Z","Toronto Raptors","Detroit Pistons","Little Caesars Arena",""),
]

def _format_rows(rows):
    df = pd.DataFrame(rows)
    dt = pd.to_datetime(df["datetime_utc"], utc=True)
    local = dt.dt.tz_convert(WARSAW)
    df["date_label"] = local.dt.strftime("%a, %d %b")
    df["time_local"] = local.dt.strftime("%H:%M")
    df["sort_dt"] = dt
    return df.sort_values("sort_dt").reset_index(drop=True)

def _fallback():
    return _format_rows([{
        "datetime_utc": dt,
        "away": away,
        "home": home,
        "venue": venue,
        "special": special,
        "status": "Upcoming",
    } for dt, away, home, venue, special in FALLBACK_GAMES])

def _fetch_espn():
    rows = []
    headers = {"User-Agent": "RadarValue/0.6"}
    day = datetime(2026, 10, 3)
    end = datetime(2026, 10, 19)

    while day <= end:
        url = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard"
        response = requests.get(
            url,
            params={"dates": day.strftime("%Y%m%d"), "limit": 100},
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()

        for event in payload.get("events", []):
            season_type = event.get("season", {}).get("type")
            if season_type not in (None, 1):
                continue

            comps = event.get("competitions", [])
            if not comps:
                continue
            comp = comps[0]
            competitors = comp.get("competitors", [])
            home = next((x for x in competitors if x.get("homeAway") == "home"), None)
            away = next((x for x in competitors if x.get("homeAway") == "away"), None)
            if not home or not away:
                continue

            rows.append({
                "datetime_utc": event.get("date"),
                "away": away.get("team", {}).get("displayName", "Away"),
                "home": home.get("team", {}).get("displayName", "Home"),
                "venue": comp.get("venue", {}).get("fullName", ""),
                "special": "",
                "status": event.get("status", {}).get("type", {}).get("description", "Upcoming"),
            })
        day += timedelta(days=1)

    if not rows:
        raise RuntimeError("Schedule feed returned no preseason events.")

    df = _format_rows(rows)
    return df.drop_duplicates(subset=["datetime_utc","away","home"]).reset_index(drop=True)

def get_preseason_schedule():
    try:
        return (
            _fetch_espn(),
            "live schedule feed",
            "Times shown in Europe/Warsaw. Official fallback is used automatically if the live feed fails.",
        )
    except Exception:
        return (
            _fallback(),
            "NBA official fallback schedule",
            "Times shown in Europe/Warsaw. Live feed unavailable, so bundled schedule is displayed.",
        )
