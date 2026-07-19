
import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Radar Value — Historical Replay",
    page_icon="📡",
    layout="wide",
)

DATA_PATH = Path(__file__).parent / "data" / "game7_demo.csv"

st.markdown("""
<style>
:root {
    --rv-green: #7CFF72;
    --rv-orange: #FF9F43;
    --rv-red: #FF5D73;
    --rv-bg: #070A0F;
    --rv-card: #101722;
    --rv-muted: #91A0B5;
}
.stApp { background: radial-gradient(circle at 15% 0%, #13241b 0%, #070A0F 28%, #070A0F 100%); }
.block-container { max-width: 1400px; padding-top: 1.4rem; }
h1, h2, h3 { letter-spacing: -0.03em; }
.rv-kicker { color: var(--rv-green); font-weight: 800; letter-spacing: .16em; font-size: .78rem; }
.rv-muted { color: var(--rv-muted); }
.rv-card {
    background: linear-gradient(145deg, rgba(18,27,40,.98), rgba(10,15,23,.98));
    border: 1px solid rgba(124,255,114,.14);
    border-radius: 22px;
    padding: 22px;
    box-shadow: 0 18px 45px rgba(0,0,0,.28);
}
.rv-score {
    font-size: 4.8rem;
    line-height: .95;
    font-weight: 900;
    color: var(--rv-green);
}
.rv-pill {
    display: inline-block;
    padding: 6px 11px;
    border-radius: 999px;
    background: rgba(124,255,114,.1);
    color: var(--rv-green);
    font-weight: 800;
    font-size: .78rem;
}
.rv-hit { color: var(--rv-green); font-weight: 900; }
.rv-miss { color: var(--rv-red); font-weight: 900; }
div[data-testid="stMetric"] {
    background: rgba(16,23,34,.85);
    border: 1px solid rgba(255,255,255,.07);
    padding: 14px 16px;
    border-radius: 16px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    return pd.read_csv(DATA_PATH)

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, v))

def calculate_projection(row):
    return (
        row["avg5"] * 0.34
        + row["avg10"] * 0.20
        + row["series_avg"] * 0.28
        + row["line"] * 0.18
        + row["minutes_trend"] * 0.35
        + row["usage_trend"] * 0.25
    )

def calculate_radar_score(row, projection):
    edge = projection - row["line"]
    edge_component = clamp(50 + edge * 6)
    trend_component = clamp(50 + row["minutes_trend"] * 7 + row["usage_trend"] * 5)
    hit_component = row["hit_rate_5"] * 100
    context_component = ((row["matchup_score"] + row["role_score"] + row["market_lag"]) / 30) * 100

    score = (
        edge_component * 0.34
        + trend_component * 0.20
        + hit_component * 0.16
        + context_component * 0.30
    )
    return round(clamp(score), 1)

df = load_data()
df["projection"] = df.apply(calculate_projection, axis=1)
df["edge"] = df["projection"] - df["line"]
df["radar_score"] = df.apply(lambda r: calculate_radar_score(r, r["projection"]), axis=1)
df["pick"] = df["edge"].apply(lambda x: "OVER" if x >= 0 else "UNDER")
df["result"] = df.apply(
    lambda r: "HIT" if ((r["pick"] == "OVER" and r["actual"] > r["line"]) or
                        (r["pick"] == "UNDER" and r["actual"] < r["line"])) else "MISS",
    axis=1,
)
df = df.sort_values("radar_score", ascending=False).reset_index(drop=True)
top = df.iloc[0]

st.markdown('<div class="rv-kicker">RADAR VALUE · HISTORICAL REPLAY</div>', unsafe_allow_html=True)
st.title("Spurs @ Thunder — Game 7")
st.caption("Western Conference Finals · 30 maja 2026 · widok symulowany tak, jak przed rozpoczęciem meczu")

left, right = st.columns([1.35, .65], gap="large")

with left:
    st.markdown(f"""
    <div class="rv-card">
        <div class="rv-pill">TOP RADAR PICK</div>
        <h2 style="margin:14px 0 4px">{top['player']}</h2>
        <div class="rv-muted">{top['market']} · linia {top['line']:.1f}</div>
        <div style="display:flex;align-items:end;gap:26px;margin-top:22px">
            <div>
                <div class="rv-score">{top['radar_score']:.0f}</div>
                <div class="rv-muted">RADAR SCORE</div>
            </div>
            <div style="padding-bottom:8px">
                <div style="font-size:1.35rem;font-weight:900">{top['pick']}</div>
                <div class="rv-muted">projekcja {top['projection']:.1f} · edge {top['edge']:+.1f}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with right:
    st.markdown("""
    <div class="rv-card">
        <div class="rv-kicker">GAME CONTEXT</div>
        <h3 style="margin-bottom:8px">Winner takes the West</h3>
        <div class="rv-muted">Seria 3–3 · mecz w Oklahoma City</div>
        <hr style="border-color:rgba(255,255,255,.08)">
        <b>Tryb:</b> pre-game snapshot<br>
        <b>Rynek:</b> punkty zawodników<br>
        <b>Walidacja:</b> wynik odkrywany niżej
    </div>
    """, unsafe_allow_html=True)

st.subheader("Radar board")
show_cols = ["player","team","line","projection","edge","radar_score","pick"]
board = df[show_cols].copy()
board.columns = ["Player","Team","Line","Projection","Edge","Radar Score","Signal"]
board["Line"]=board["Line"].map(lambda x:f"{x:.1f}")
board["Projection"]=board["Projection"].map(lambda x:f"{x:.1f}")
board["Edge"]=board["Edge"].map(lambda x:f"{x:+.1f}")
board["Radar Score"]=board["Radar Score"].map(lambda x:f"{x:.1f}")

st.dataframe(
    board,
    use_container_width=True
)

st.subheader("Dlaczego model tak ocenił zawodników?")
selected_player = st.selectbox("Wybierz zawodnika", df["player"].tolist())
p = df[df["player"] == selected_player].iloc[0]

m1, m2, m3, m4 = st.columns(4)
m1.metric("Średnia L5", f"{p['avg5']:.1f}")
m2.metric("Średnia L10", f"{p['avg10']:.1f}")
m3.metric("Średnia w serii", f"{p['series_avg']:.1f}")
m4.metric("Minuty", f"{p['minutes_avg']:.1f}", f"{p['minutes_trend']:+.1f}")

c1, c2, c3 = st.columns(3)
c1.metric("Role score", f"{p['role_score']:.1f}/10")
c2.metric("Matchup score", f"{p['matchup_score']:.1f}/10")
c3.metric("Market lag", f"{p['market_lag']:.1f}/10")

chart_data = pd.DataFrame({
    "Metric": ["Book line", "L5", "L10", "Series", "Projection"],
    "Value": [p["line"], p["avg5"], p["avg10"], p["series_avg"], p["projection"]]
}).set_index("Metric")
st.bar_chart(chart_data)

st.divider()
st.subheader("Post-game validation")
reveal = st.toggle("Odkryj wynik Game 7")

if reveal:
    hits = int((df["result"] == "HIT").sum())
    total = len(df)
    st.metric("Skuteczność demo", f"{hits}/{total}", f"{hits/total:.0%}")
    result_view = df[["player","line","projection","pick","actual","result"]].copy()
    result_view.columns = ["Player","Line","Projection","Pick","Actual points","Result"]
    result_view["Line"]=result_view["Line"].map(lambda x:f"{x:.1f}")
    result_view["Projection"]=result_view["Projection"].map(lambda x:f"{x:.1f}")
    st.dataframe(
        result_view,
        use_container_width=True
    )
    st.caption("To pojedynczy mecz i nie jest dowodem przewagi modelu. To prototyp ekranu oraz mechanizmu backtestu.")
else:
    st.info("Wyniki są ukryte, aby dashboard zachowywał się jak analiza przedmeczowa.")

with st.expander("Założenia wersji beta"):
    st.markdown("""
- Dane wejściowe L5/L10, trendy i oceny kontekstowe są zestawem demonstracyjnym do budowy interfejsu.
- Linie w pliku CSV są edytowalne. Przed uznaniem ich za archiwalne należy potwierdzić je w wiarygodnym źródle kursów.
- Wyniki Game 7 użyte do walidacji: SGA 35, Wembanyama 22, Castle 16, Fox 15.
- Docelowo dane demonstracyjne zastąpimy snapshotem z API oraz archiwum linii bukmacherskich.
""")
