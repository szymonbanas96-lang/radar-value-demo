import math
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import pandas as pd
import streamlit as st

from schedule_service import get_preseason_schedule
from injury_service import get_team_roster

st.set_page_config(
    page_title="Radar Value — Preseason 2026",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.stApp {
    background:
        radial-gradient(circle at 12% 0%, rgba(52,211,153,.08), transparent 28%),
        radial-gradient(circle at 95% 15%, rgba(249,115,22,.06), transparent 25%),
        #070a0d;
    color:#f4f7f8;
}
[data-testid="stHeader"] { background: rgba(7,10,13,.78); }
.block-container { max-width:1280px; padding-top:1.2rem; padding-bottom:3rem; }

.logo-wrap { text-align:center; margin-top:-10px; margin-bottom:4px; }
.subtitle { text-align:center; color:#91a0aa; margin-bottom:1.2rem; }

.hero {
    border:1px solid #1b2830; border-radius:20px; padding:20px 22px;
    background:linear-gradient(135deg, rgba(14,20,25,.96), rgba(8,12,15,.96));
    margin-bottom:16px;
}
.eyebrow {
    color:#35e88c; font-size:.76rem; letter-spacing:.16em;
    text-transform:uppercase; font-weight:800;
}
.hero-title { font-size:1.5rem; font-weight:800; margin:7px 0 5px 0; }
.muted { color:#91a0aa; }

.top3-card {
    border:1px solid #1c2b33; border-radius:18px; padding:18px;
    background:#0d1216; min-height:150px;
}
.rank { font-size:.74rem; color:#f97316; font-weight:900; letter-spacing:.12em; }
.pick-title { font-size:1.03rem; font-weight:800; margin:8px 0 4px 0; }
.pick-empty { color:#71808a; font-size:.88rem; }

.game-shell {
    border:1px solid #1b2830; border-radius:20px; padding:18px;
    background:#0d1216; margin:0 0 16px 0;
}
.game-head {
    display:flex; justify-content:space-between; gap:12px; align-items:flex-start;
    margin-bottom:14px;
}
.game-title { font-size:1.22rem; font-weight:850; }
.game-meta { color:#91a0aa; font-size:.84rem; margin-top:4px; }
.badge {
    display:inline-block; border-radius:999px; padding:5px 10px;
    font-size:.72rem; font-weight:800;
}
.badge-wait { background:#25221a; color:#f4be62; }
.badge-live { background:#341818; color:#ff7777; }
.badge-final { background:#1b242a; color:#aebbc3; }

.value-card {
    border:1px solid #20322a; border-radius:14px; padding:13px 14px;
    background:linear-gradient(135deg, rgba(13,28,20,.85), rgba(13,18,22,.92));
    margin-bottom:12px;
}
.value-title { font-weight:800; }
.value-empty { color:#71808a; margin-top:4px; font-size:.86rem; }

.roster-box {
    border:1px solid #172129; border-radius:14px; padding:14px;
    background:#0a0f13; min-height:104px;
}
.team-name { font-weight:850; margin-bottom:7px; }
.roster-empty { color:#71808a; font-size:.86rem; }

.score { font-size:2.1rem; font-weight:900; color:#35e88c; }
.tiny { font-size:.76rem; color:#71808a; }
</style>
""", unsafe_allow_html=True)

WARSAW = ZoneInfo("Europe/Warsaw")
now = datetime.now(WARSAW)
schedule, schedule_source, schedule_note = get_preseason_schedule()

@st.cache_data(ttl=600, show_spinner=False)
def cached_roster(team_name):
    return get_team_roster(team_name)

STATUS_STYLE = {
    "OUT": ("#ff6b6b", "#35191b"),
    "DOUBTFUL": ("#ff8b62", "#352018"),
    "QUESTIONABLE": ("#ffc857", "#332a17"),
    "PROBABLE": ("#79e6a7", "#173124"),
    "DAY-TO-DAY": ("#ffd166", "#332b18"),
    "AVAILABLE": ("#8ea0aa", "#172129"),
}

def roster_html(team_name):
    roster, source = cached_roster(team_name)
    if not roster:
        return f"""
        <div class="roster-box">
          <div class="team-name">{team_name}</div>
          <div class="roster-empty">Roster/injury feed is not available yet.</div>
        </div>
        """
    rows = []
    for p in roster:
        status = p["status"]
        fg, bg = STATUS_STYLE.get(status, ("#8ea0aa", "#172129"))
        reason = f"<div style='color:#71808a;font-size:.72rem'>{p['reason']}</div>" if p.get("reason") else ""
        rows.append(f"""
        <div style='display:flex;justify-content:space-between;gap:10px;padding:7px 0;border-bottom:1px solid #172129'>
          <div><b>{p['name']}</b> <span style='color:#71808a;font-size:.76rem'>{p.get('position','')}</span>{reason}</div>
          <span style='height:fit-content;background:{bg};color:{fg};border-radius:999px;padding:3px 7px;font-size:.68rem;font-weight:800'>{status}</span>
        </div>
        """)
    return f"""
    <div class="roster-box">
      <div class="team-name">{team_name}</div>
      <div style='color:#71808a;font-size:.72rem;margin-bottom:5px'>{source} · refresh ≤10 min</div>
      {''.join(rows)}
    </div>
    """


def game_status(row):
    status = str(row.get("status", "Upcoming")).lower()
    if "final" in status:
        return "FINAL", "badge-final"
    if "live" in status or "in progress" in status:
        return "LIVE", "badge-live"
    return "WAITING FOR LINES", "badge-wait"

def value_score(projection: float, line: float, confidence: float = 0.72):
    edge = projection - line
    normalized = abs(edge) / max(1.0, math.sqrt(max(projection, 1.0)))
    score = 50 + normalized * 24 + (confidence - 0.5) * 26
    return max(0, min(99, round(score))), edge

logo = Path("assets/radar_value_logo.png")
if logo.exists():
    c1, c2, c3 = st.columns([1, 1.15, 1])
    with c2:
        st.image(str(logo), use_container_width=True)
st.markdown('<div class="subtitle">See the edge. Value the game. · Preseason 2026</div>', unsafe_allow_html=True)

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=600000, limit=None, key="radar_live_refresh")
except Exception:
    pass

home_tab, scanner_tab, line_tab, system_tab = st.tabs(
    ["🏠 Home", "📡 Market Scanner", "🎚️ Line Lab", "⚙️ System"]
)

with home_tab:
    preseason_start = datetime(2026, 10, 3, 23, 0, tzinfo=WARSAW)
    delta = preseason_start - now
    countdown = f"{delta.days}d {delta.seconds // 3600}h" if delta.total_seconds() > 0 else "LIVE"

    st.markdown(f"""
    <div class="hero">
        <div class="eyebrow">2026–27 NBA</div>
        <div class="hero-title">Preseason Command Center</div>
        <div class="muted">Preseason status: <b>{countdown}</b></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("## 🏆 Top 3 Value — Today")
    top_cols = st.columns(3)
    for i, col in enumerate(top_cols, start=1):
        with col:
            st.markdown(f"""
            <div class="top3-card">
                <div class="rank">#{i}</div>
                <div class="pick-title">Waiting for market data</div>
                <div class="pick-empty">The strongest value pick of the day will appear here after odds and player data are connected.</div>
            </div>
            """, unsafe_allow_html=True)

    refresh_col, label_col = st.columns([1,4])
    with refresh_col:
        if st.button("↻ Refresh live data", use_container_width=True):
            cached_roster.clear()
            st.rerun()
    with label_col:
        st.caption("Rosters and availability refresh automatically every 10 minutes.")

    st.markdown("## 🏀 Games")

    filter_cols = st.columns([1.2,1,1])
    with filter_cols[0]:
        team_options = ["All teams"] + sorted(set(schedule["away"]).union(set(schedule["home"])))
        selected_team = st.selectbox("Team", team_options)
    with filter_cols[1]:
        date_options = ["All dates"] + list(dict.fromkeys(schedule["date_label"].tolist()))
        selected_date = st.selectbox("Date", date_options)
    with filter_cols[2]:
        only_upcoming = st.toggle("Upcoming only", value=True)

    shown = schedule.copy()
    if selected_team != "All teams":
        shown = shown[(shown["away"] == selected_team) | (shown["home"] == selected_team)]
    if selected_date != "All dates":
        shown = shown[shown["date_label"] == selected_date]
    if only_upcoming:
        shown = shown[pd.to_datetime(shown["datetime_utc"], utc=True) >= pd.Timestamp.now(tz="UTC")]

    for _, row in shown.head(12).iterrows():
        label, badge_class = game_status(row)

        st.markdown(f"""
        <div class="game-shell">
            <div class="game-head">
                <div>
                    <div class="game-title">{row['away']} @ {row['home']}</div>
                    <div class="game-meta">{row['date_label']} · {row['time_local']} · {row.get('venue','')}</div>
                </div>
                <div><span class="badge {badge_class}">{label}</span></div>
            </div>

            <div class="value-card">
                <div class="eyebrow">TOP VALUE — THIS GAME</div>
                <div class="value-title">Waiting for sportsbook lines</div>
                <div class="value-empty">The best Points / Assists / Rebounds / PRA edge from this matchup will appear here.</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        r1, r2 = st.columns(2)
        with r1:
            st.markdown(roster_html(row["away"]), unsafe_allow_html=True)
        with r2:
            st.markdown(roster_html(row["home"]), unsafe_allow_html=True)
        st.write("")

    st.caption(f"Schedule source: {schedule_source}. {schedule_note}")

with scanner_tab:
    st.markdown("## 📡 Market Scanner")
    st.write("Ranks the largest gaps between Radar projections and bookmaker lines.")
    st.segmented_control("Market", ["Points","Assists","Rebounds","PRA"], default="Points")
    st.dataframe(pd.DataFrame(columns=[
        "Rank","Player","Game","Market","Book line","Radar projection","Edge","Radar Value","Signal"
    ]), use_container_width=True, hide_index=True)

with line_tab:
    st.markdown("## 🎚️ Line Lab")
    demos = {
        "Demo Guard — Points": {"projection":29.8,"market_line":27.5,"confidence":0.76},
        "Demo Center — Rebounds": {"projection":10.6,"market_line":8.5,"confidence":0.74},
        "Demo Guard — Assists": {"projection":8.9,"market_line":7.5,"confidence":0.71},
        "Demo Star — PRA": {"projection":43.4,"market_line":39.5,"confidence":0.78},
    }
    chosen = st.selectbox("Demo player / market", list(demos))
    d = demos[chosen]
    custom_line = st.slider(
        "Your bookmaker line",
        min_value=float(max(.5, d["market_line"]-6)),
        max_value=float(d["market_line"]+6),
        value=float(d["market_line"]),
        step=.5,
    )
    score, edge = value_score(d["projection"], custom_line, d["confidence"])
    signal = "OVER" if edge > 0 else "UNDER" if edge < 0 else "PASS"
    c1,c2,c3 = st.columns(3)
    with c1: st.metric("Radar projection", f"{d['projection']:.1f}")
    with c2: st.metric("Edge", f"{edge:+.1f}")
    with c3:
        st.markdown(f'<div class="value-card"><div class="tiny">RADAR VALUE</div><div class="score">{score}</div><b>{signal}</b> at {custom_line:.1f}</div>', unsafe_allow_html=True)

with system_tab:
    st.markdown("## ⚙️ Preseason readiness")
    readiness = pd.DataFrame([
        ["Schedule","ACTIVE"],
        ["Top 3 day value","UI READY"],
        ["Top value per game","UI READY"],
        ["Rosters + injury statuses","LIVE / AUTO 10 MIN"],
        ["Points Radar","UI READY"],
        ["Assists Radar","UI READY"],
        ["Rebounds Radar","UI READY"],
        ["PRA Radar","UI READY"],
        ["Odds feed","PENDING"],
        ["Line slider","ACTIVE"],
        ["Game 7","REMOVED"],
    ], columns=["Module","Status"])
    st.dataframe(readiness, use_container_width=True, hide_index=True)
