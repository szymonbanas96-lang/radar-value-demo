import math
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from schedule_service import get_preseason_schedule

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
.block-container { max-width:1280px; padding-top:1.4rem; padding-bottom:3rem; }
.brand { display:flex; align-items:center; gap:14px; margin-bottom:4px; }
.brand-mark {
    width:48px; height:48px; border-radius:50%; border:2px solid #35e88c;
    position:relative; box-shadow:0 0 28px rgba(53,232,140,.18);
}
.brand-mark:before,.brand-mark:after { content:""; position:absolute; background:#35e88c55; }
.brand-mark:before { width:2px; height:100%; left:50%; top:0; }
.brand-mark:after { height:2px; width:100%; top:50%; left:0; }
.brand-dot {
    width:9px; height:9px; border-radius:50%; background:#f97316;
    position:absolute; left:28px; top:11px; box-shadow:0 0 12px rgba(249,115,22,.65);
}
.brand h1 { margin:0; font-size:2rem; letter-spacing:-.04em; }
.brand h1 span { color:#35e88c; }
.subtitle { color:#91a0aa; margin:.1rem 0 1.2rem 0; }
.hero {
    border:1px solid #1b2830; border-radius:20px; padding:22px 24px;
    background:linear-gradient(135deg, rgba(14,20,25,.96), rgba(8,12,15,.96));
    margin-bottom:18px;
}
.eyebrow {
    color:#35e88c; font-size:.78rem; letter-spacing:.16em; text-transform:uppercase; font-weight:700;
}
.hero-title { font-size:1.55rem; font-weight:750; margin:8px 0 6px 0; }
.muted { color:#91a0aa; }
.game-card {
    border:1px solid #1b2830; border-radius:16px; padding:16px 18px;
    background:#0d1216; min-height:132px; margin-bottom:10px;
}
.game-date { color:#91a0aa; font-size:.78rem; text-transform:uppercase; letter-spacing:.08em; }
.game-team { font-size:1.04rem; font-weight:700; margin-top:7px; }
.game-meta { color:#91a0aa; font-size:.86rem; margin-top:8px; }
.status {
    display:inline-block; border-radius:999px; padding:4px 9px; font-size:.72rem;
    font-weight:700; margin-top:10px;
}
.status-wait { background:#25221a; color:#f4be62; }
.status-live { background:#341818; color:#ff7777; }
.status-final { background:#1b242a; color:#aebbc3; }
.radar-card {
    border:1px solid #1b2830; border-radius:18px; padding:18px;
    background:#0d1216; height:100%;
}
.radar-name { font-size:1.05rem; font-weight:800; margin-bottom:4px; }
.radar-empty { color:#71808a; font-size:.88rem; margin-top:12px; }
.orange { color:#f97316; }
.value-box {
    border:1px solid #20322a; border-radius:18px; padding:18px;
    background:linear-gradient(135deg, rgba(13,28,20,.85), rgba(13,18,22,.92));
}
.score { font-size:2.35rem; font-weight:850; letter-spacing:-.05em; color:#35e88c; }
.tiny { font-size:.78rem; color:#71808a; }
</style>
""", unsafe_allow_html=True)

WARSAW = ZoneInfo("Europe/Warsaw")
now = datetime.now(WARSAW)
schedule, schedule_source, schedule_note = get_preseason_schedule()

def game_status(row):
    status = str(row.get("status", "Upcoming")).lower()
    if "final" in status:
        return "FINAL", "status-final"
    if "live" in status or "in progress" in status:
        return "LIVE", "status-live"
    return "WAITING FOR LINES", "status-wait"

def value_score(projection: float, line: float, confidence: float = 0.72):
    edge = projection - line
    normalized = abs(edge) / max(1.0, math.sqrt(max(projection, 1.0)))
    score = 50 + normalized * 24 + (confidence - 0.5) * 26
    return max(0, min(99, round(score))), edge

def render_game_card(row):
    label, css = game_status(row)
    special = row.get("special", "")
    special_html = f"<div class='game-meta orange'>{special}</div>" if special else ""
    st.markdown(f"""
    <div class="game-card">
        <div class="game-date">{row['date_label']} · {row['time_local']}</div>
        <div class="game-team">{row['away']} <span class="muted">@</span> {row['home']}</div>
        <div class="game-meta">{row.get('venue','')}</div>
        {special_html}
        <span class="status {css}">{label}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="brand">
  <div class="brand-mark"><div class="brand-dot"></div></div>
  <div><h1>RADAR <span>VALUE</span></h1></div>
</div>
<div class="subtitle">See the edge. Value the game. · Preseason 2026</div>
""", unsafe_allow_html=True)

home_tab, scanner_tab, line_tab, system_tab = st.tabs(
    ["🏠 Home", "📡 Market Scanner", "🎚️ Line Lab", "⚙️ System"]
)

with home_tab:
    preseason_start = datetime(2026, 10, 3, 23, 0, tzinfo=WARSAW)
    delta = preseason_start - now
    if delta.total_seconds() > 0:
        countdown = f"{delta.days}d {delta.seconds // 3600}h"
        hero_copy = f"Preseason starts in <b>{countdown}</b>. Radar is in preparation mode."
    else:
        hero_copy = "Preseason is underway. Schedule and market modules are active."

    st.markdown(f"""
    <div class="hero">
        <div class="eyebrow">2026–27 NBA</div>
        <div class="hero-title">Preseason Command Center</div>
        <div class="muted">{hero_copy}</div>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Preseason games", len(schedule))
    with m2:
        future = schedule[pd.to_datetime(schedule["datetime_utc"], utc=True) >= pd.Timestamp.now(tz="UTC")]
        st.metric("Upcoming", len(future))
    with m3: st.metric("Markets tracked", 4)
    with m4: st.metric("Radar Ready", 0)

    st.markdown("### 🏀 Preseason Schedule")
    c1, c2, c3 = st.columns([1.25, 1, 1])
    with c1:
        teams = ["All teams"] + sorted(set(schedule["away"]).union(set(schedule["home"])))
        selected_team = st.selectbox("Team", teams)
    with c2:
        dates = ["All dates"] + list(dict.fromkeys(schedule["date_label"].tolist()))
        selected_date = st.selectbox("Date", dates)
    with c3:
        only_upcoming = st.toggle("Upcoming only", value=True)

    shown = schedule.copy()
    if selected_team != "All teams":
        shown = shown[(shown["away"] == selected_team) | (shown["home"] == selected_team)]
    if selected_date != "All dates":
        shown = shown[shown["date_label"] == selected_date]
    if only_upcoming:
        shown = shown[pd.to_datetime(shown["datetime_utc"], utc=True) >= pd.Timestamp.now(tz="UTC")]

    if shown.empty:
        st.info("No games match these filters.")
    else:
        cols = st.columns(3)
        for i, (_, row) in enumerate(shown.head(18).iterrows()):
            with cols[i % 3]:
                render_game_card(row)

    st.caption(f"Schedule source: {schedule_source}. {schedule_note}")

    st.markdown("### 🎯 Top Radar Value")
    cols = st.columns(4)
    for col, name, code in zip(
        cols,
        ["Points Radar", "Assists Radar", "Rebounds Radar", "PRA Radar"],
        ["PTS", "AST", "REB", "PRA"],
    ):
        with col:
            st.markdown(f"""
            <div class="radar-card">
                <div class="eyebrow">{code}</div>
                <div class="radar-name">{name}</div>
                <div class="radar-empty">Waiting for sportsbook lines and preseason player data.</div>
            </div>
            """, unsafe_allow_html=True)

with scanner_tab:
    st.markdown("## 📡 Market Scanner")
    st.write("Main workflow: scan the whole market first and rank the biggest gaps between the Radar model and bookmaker lines.")
    st.segmented_control("Market", ["Points", "Assists", "Rebounds", "PRA"], default="Points")
    f1, f2, f3 = st.columns(3)
    with f1: st.slider("Minimum Radar Value", 50, 99, 75)
    with f2: st.selectbox("Side", ["Both", "OVER", "UNDER"])
    with f3: st.selectbox("Games", ["All preseason games", "Today", "Next 24h"])

    st.markdown("""
    <div class="hero">
        <div class="eyebrow">Scanner status</div>
        <div class="hero-title">Waiting for odds feed</div>
        <div class="muted">When the odds provider is connected, this area will rank the biggest line discrepancies automatically.</div>
    </div>
    """, unsafe_allow_html=True)

    st.dataframe(pd.DataFrame(columns=[
        "Rank","Player","Game","Market","Book line","Radar projection","Edge","Radar Value","Signal"
    ]), use_container_width=True, hide_index=True)

with line_tab:
    st.markdown("## 🎚️ Line Lab")
    st.write("Prototype of the slider. In production the projection comes from Radar automatically — the user changes only the bookmaker line.")
    demos = {
        "Demo Guard — Points": {"projection": 29.8, "market_line": 27.5, "confidence": 0.76},
        "Demo Center — Rebounds": {"projection": 10.6, "market_line": 8.5, "confidence": 0.74},
        "Demo Guard — Assists": {"projection": 8.9, "market_line": 7.5, "confidence": 0.71},
        "Demo Star — PRA": {"projection": 43.4, "market_line": 39.5, "confidence": 0.78},
    }
    chosen = st.selectbox("Demo player / market", list(demos))
    d = demos[chosen]
    custom_line = st.slider(
        "Your bookmaker line",
        min_value=float(max(0.5, d["market_line"] - 6)),
        max_value=float(d["market_line"] + 6),
        value=float(d["market_line"]),
        step=0.5,
    )
    score, edge = value_score(d["projection"], custom_line, d["confidence"])
    signal = "OVER" if edge > 0 else "UNDER" if edge < 0 else "PASS"

    v1, v2, v3 = st.columns(3)
    with v1: st.metric("Radar projection", f"{d['projection']:.1f}")
    with v2: st.metric("Edge", f"{edge:+.1f}", delta=f"{edge:+.1f} vs line")
    with v3:
        st.markdown(f"""
        <div class="value-box">
            <div class="tiny">RADAR VALUE</div>
            <div class="score">{score}</div>
            <div><b>{signal}</b> at {custom_line:.1f}</div>
        </div>
        """, unsafe_allow_html=True)
    st.caption("Demo UI only. Production values will come from separate Points / Assists / Rebounds / PRA models.")

with system_tab:
    st.markdown("## ⚙️ Preseason readiness")
    readiness = pd.DataFrame([
        ["Schedule","ACTIVE","Automatic live feed + official fallback"],
        ["Points Radar","UI READY","Model/data feed next"],
        ["Assists Radar","UI READY","Model/data feed next"],
        ["Rebounds Radar","UI READY","Model/data feed next"],
        ["PRA Radar","UI READY","Model/data feed next"],
        ["Bookmaker odds","PENDING","Connect odds API"],
        ["Injuries / availability","PENDING","Connect data source"],
        ["Line override slider","ACTIVE","Working prototype"],
        ["Game 7 demo","REMOVED","Not shown in preseason product"],
    ], columns=["Module","Status","Notes"])
    st.dataframe(readiness, use_container_width=True, hide_index=True)
    st.success(
        "Product rule: Radar Value scans the market and finds potentially mispriced lines. "
        "A custom bookmaker line can then be entered with the slider to recalculate value instantly."
    )
