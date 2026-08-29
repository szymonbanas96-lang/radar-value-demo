
import requests
from datetime import datetime, timezone

TEAM_IDS = {
    "Atlanta Hawks":"1","Boston Celtics":"2","Brooklyn Nets":"17","Charlotte Hornets":"30",
    "Chicago Bulls":"4","Cleveland Cavaliers":"5","Dallas Mavericks":"6","Denver Nuggets":"7",
    "Detroit Pistons":"8","Golden State Warriors":"9","Houston Rockets":"10","Indiana Pacers":"11",
    "LA Clippers":"12","Los Angeles Clippers":"12","Los Angeles Lakers":"13","Memphis Grizzlies":"29",
    "Miami Heat":"14","Milwaukee Bucks":"15","Minnesota Timberwolves":"16","New Orleans Pelicans":"3",
    "New York Knicks":"18","Oklahoma City Thunder":"25","Orlando Magic":"19","Philadelphia 76ers":"20",
    "Phoenix Suns":"21","Portland Trail Blazers":"22","Sacramento Kings":"23","San Antonio Spurs":"24",
    "Toronto Raptors":"28","Utah Jazz":"26","Washington Wizards":"27"
}

STATUS_ORDER = {
    "OUT": 0, "DOUBTFUL": 1, "QUESTIONABLE": 2, "PROBABLE": 3,
    "DAY-TO-DAY": 4, "AVAILABLE": 5, "ACTIVE": 5, "UNKNOWN": 6
}

def normalize_status(value):
    raw = (value or "").strip().upper()
    aliases = {
        "O":"OUT","OUT":"OUT",
        "D":"DOUBTFUL","DOUBTFUL":"DOUBTFUL",
        "Q":"QUESTIONABLE","QUESTIONABLE":"QUESTIONABLE",
        "P":"PROBABLE","PROBABLE":"PROBABLE",
        "DTD":"DAY-TO-DAY","DAY-TO-DAY":"DAY-TO-DAY",
        "ACTIVE":"AVAILABLE","AVAILABLE":"AVAILABLE",
    }
    return aliases.get(raw, raw if raw else "AVAILABLE")

def _extract_status(athlete):
    injuries = athlete.get("injuries") or []
    if injuries:
        inj = injuries[0]
        status = (
            inj.get("status")
            or inj.get("type", {}).get("description")
            or inj.get("type", {}).get("name")
            or inj.get("type", {}).get("abbreviation")
        )
        detail = inj.get("details", {}) or {}
        reason = detail.get("detail") or detail.get("type") or inj.get("shortComment") or ""
        return normalize_status(status), reason
    return "AVAILABLE", ""

def get_team_roster(team_name):
    team_id = TEAM_IDS.get(team_name)
    if not team_id:
        return [], "unknown team"

    urls = [
        f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_id}/roster",
        f"https://site.web.api.espn.com/apis/common/v3/sports/basketball/nba/teams/{team_id}/roster",
    ]
    headers = {"User-Agent":"Mozilla/5.0 RadarValue/0.8"}
    last_error = None

    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=8)
            r.raise_for_status()
            data = r.json()
            athletes = data.get("athletes", [])
            # Some ESPN responses group athletes by position.
            if athletes and isinstance(athletes[0], dict) and "items" in athletes[0]:
                athletes = [item for group in athletes for item in group.get("items", [])]

            roster = []
            for a in athletes:
                name = a.get("fullName") or a.get("displayName") or a.get("athlete", {}).get("displayName")
                if not name:
                    continue
                status, reason = _extract_status(a)
                pos = a.get("position", {})
                if isinstance(pos, dict):
                    pos = pos.get("abbreviation") or pos.get("name") or ""
                roster.append({
                    "name": name,
                    "position": pos or "",
                    "status": status,
                    "reason": reason,
                })

            if roster:
                roster.sort(key=lambda x: (STATUS_ORDER.get(x["status"], 6), x["name"]))
                return roster, "ESPN live roster"
        except Exception as e:
            last_error = str(e)

    return [], f"roster feed unavailable: {last_error or 'no data'}"

def fetched_at():
    return datetime.now(timezone.utc).isoformat()
