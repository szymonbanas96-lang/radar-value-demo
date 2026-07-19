from pathlib import Path
import subprocess
import sys

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"

st.set_page_config(
    page_title="Radar Value",
    page_icon=str(ASSETS / "favicon.png"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- Styling ----------
css_path = ASSETS / "style.css"
if css_path.exists():
    st.markdown(css_path.read_text(encoding="utf-8"), unsafe_allow_html=True)

# ---------- Helpers ----------
def read_csv_safe(filename: str) -> pd.DataFrame:
    path = ROOT / filename
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception as exc:
        st.warning(f"Nie udało się wczytać {filename}: {exc}")
        return pd.DataFrame()


def num(value, default: float = 0.0) -> float:
    try:
        if pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def col_name(df: pd.DataFrame, preferred: str, fallback: str | None = None):
    if preferred in df.columns:
        return preferred
    if fallback and fallback in df.columns:
        return fallback
    return None


def grade_results(df: pd.DataFrame) -> pd.DataFrame:
    required = {"actual_pra", "prediction", "book_line"}
    if df.empty or not required.issubset(df.columns):
        return df

    out = df.copy()

    def outcome(row):
        if pd.isna(row["actual_pra"]):
            return ""
        actual = num(row["actual_pra"])
        line = num(row["book_line"])
        prediction = str(row["prediction"]).upper()
        if prediction == "OVER":
            return "WIN" if actual > line else "LOSS"
        if prediction == "UNDER":
            return "WIN" if actual < line else "LOSS"
        return ""

    out["result"] = out.apply(outcome, axis=1)

    def profit(row):
        if row["result"] == "WIN":
            return num(row.get("odds", 1.90), 1.90) - 1
        if row["result"] == "LOSS":
            return -1.0
        return 0.0

    out["profit"] = out.apply(profit, axis=1)
    return out


def section(eyebrow: str, title: str, subtitle: str | None = None):
    st.markdown(
        f'<div class="rv-eyebrow">{eyebrow}</div>',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    if subtitle:
        st.markdown(
            f'<div class="rv-subtitle">{subtitle}</div>',
            unsafe_allow_html=True,
        )


def player_card(row: pd.Series):
    name = str(row.get("name", "Unknown player"))
    score = num(row.get("score"))
    signal = str(row.get("signal", "—"))
    edge = num(row.get("real_edge", row.get("edge", 0)))
    line = num(row.get("book_line", 0))
    pra5 = num(row.get("pra5", 0))
    minutes = num(row.get("minutes_trend", 0))

    left, right = st.columns([4, 1])
    with left:
        st.markdown(
            f"""
<div class="rv-player-name">{name}</div>
<div class="rv-player-signal">{signal}</div>
<div class="rv-player-meta">
Edge {edge:+.1f} · Line {line:.1f} · PRA5 {pra5:.1f} · Minutes {minutes:+.1f}
</div>
""",
            unsafe_allow_html=True,
        )
    with right:
        st.markdown(
            f'<div class="rv-score">{score:.1f}</div>',
            unsafe_allow_html=True,
        )


# ---------- Data ----------
radar_df = read_csv_safe("radar_results.csv")
history_df = read_csv_safe("history.csv")
results_df = grade_results(read_csv_safe("results.csv"))

# ---------- Header ----------
logo_col, status_col = st.columns([5, 1])

with logo_col:
    if (ASSETS / "logo_horizontal.png").exists():
        st.image(str(ASSETS / "logo_horizontal.png"), width=360)
    else:
        st.title("📡 RADAR VALUE")
    st.caption("NBA market intelligence platform")

with status_col:
    st.markdown(
        '<div class="rv-pill">● ALPHA v0.3</div>',
        unsafe_allow_html=True,
    )

refresh_col, note_col = st.columns([1.2, 4.8])
with refresh_col:
    refresh = st.button("📡 Scan Radar")
with note_col:
    st.caption(
        "Demo korzysta z radar_results.csv. Skan uruchamia aktualny main.py."
    )

if refresh:
    with st.status("📡 Scanning today's games...", expanded=True) as status:
        st.write("🏀 Loading players and rotations...")
        run = subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        st.write("📈 Calculating Radar Score...")
        if run.returncode == 0:
            status.update(label="✅ Radar ready", state="complete")
            st.rerun()
        else:
            status.update(label="❌ Radar scan failed", state="error")
            st.code(run.stderr or run.stdout or "Brak szczegółów błędu.")

if radar_df.empty:
    st.error("Brak danych w radar_results.csv.")
    st.stop()

required = {"name", "score", "signal"}
missing = required.difference(radar_df.columns)
if missing:
    st.error("Brakuje kolumn: " + ", ".join(sorted(missing)))
    st.stop()

radar_df = radar_df.copy()
radar_df["score"] = pd.to_numeric(radar_df["score"], errors="coerce").fillna(0)
radar_df = radar_df.sort_values("score", ascending=False)
top = radar_df.iloc[0]

edge_col = col_name(radar_df, "real_edge", "edge")
elite_count = (
    int(radar_df["elite_play"].fillna(False).astype(bool).sum())
    if "elite_play" in radar_df.columns
    else 0
)
strong_count = int(
    (radar_df["signal"] == "🔥 STRONG OVER TREND").sum()
)
cold_count = int(
    (radar_df["signal"] == "🔻 COLD TREND").sum()
)

# ---------- Top pick ----------
section(
    "Daily intelligence",
    "Top Radar Pick",
    "Najmocniejszy aktualny sygnał według modelu.",
)

st.markdown('<div class="rv-top-shell">', unsafe_allow_html=True)
with st.container(border=True):
    name_col, score_col = st.columns([3.7, 1.3])

    with name_col:
        st.caption("TODAY'S BEST VALUE")
        st.title(str(top["name"]))
        st.markdown(f"**{top['signal']}**")

    with score_col:
        st.metric(
            "Radar Score",
            f"{num(top['score']):.1f}",
            "out of 100",
        )

    edge = num(top.get(edge_col, 0)) if edge_col else 0
    line = num(top.get("book_line", 0))
    pra5 = num(top.get("pra5", 0))
    minutes = num(top.get("minutes_trend", 0))

    a, b, c, d = st.columns(4)
    a.metric("Real Edge", f"{edge:+.1f}")
    b.metric("Book Line", f"{line:.1f}")
    c.metric("PRA Last 5", f"{pra5:.1f}")
    d.metric("Minutes Trend", f"{minutes:+.1f}")
st.markdown("</div>", unsafe_allow_html=True)

# ---------- Snapshot ----------
section("Market overview", "Radar Snapshot")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Average Score", f"{radar_df['score'].mean():.1f}")
m2.metric("Elite Plays", elite_count)
m3.metric("Strong Overs", strong_count)
m4.metric("Cold Trends", cold_count)

# ---------- Filters ----------
section(
    "Signal explorer",
    "Today's Player Radar",
    "Filtruj sygnały i zawęź listę do najlepszych okazji.",
)

f1, f2, f3 = st.columns(3)
signals = list(radar_df["signal"].dropna().unique())

with f1:
    selected_signals = st.multiselect(
        "Signals",
        options=signals,
        default=signals,
    )

with f2:
    min_score = st.slider(
        "Minimum Radar Score",
        min_value=0,
        max_value=100,
        value=20,
    )

with f3:
    min_edge = st.slider(
        "Minimum Edge",
        min_value=-15.0,
        max_value=15.0,
        value=0.0,
        step=0.5,
    )

filtered = radar_df[
    radar_df["signal"].isin(selected_signals)
    & (radar_df["score"] >= min_score)
].copy()

if edge_col:
    filtered[edge_col] = pd.to_numeric(
        filtered[edge_col], errors="coerce"
    ).fillna(0)
    filtered = filtered[filtered[edge_col] >= min_edge]

# Native Streamlit card grid.
if filtered.empty:
    st.info("Brak zawodników spełniających filtry.")
else:
    rows = filtered.head(12).reset_index(drop=True)
    for start in range(0, len(rows), 3):
        cols = st.columns(3)
        chunk = rows.iloc[start:start + 3]
        for col, (_, row) in zip(cols, chunk.iterrows()):
            with col:
                with st.container(border=True):
                    player_card(row)
                    st.progress(
                        max(0, min(100, int(num(row.get("score"))))),
                        text="Model strength",
                    )

with st.expander("View complete radar table"):
    st.dataframe(
        filtered,
        use_container_width=True,
        hide_index=True,
    )

# ---------- History ----------
section("Performance", "History & Accuracy")

history_tab, accuracy_tab = st.tabs(
    ["Radar history", "Accuracy tracking"]
)

with history_tab:
    if history_df.empty:
        st.info("Brak history.csv. Historia pojawi się po zapisaniu skanów.")
    else:
        if "timestamp" in history_df.columns:
            history_df = history_df.sort_values(
                "timestamp", ascending=False
            )
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
        )

        if {"timestamp", "name", "score"}.issubset(history_df.columns):
            player = st.selectbox(
                "Player score history",
                options=history_df["name"].dropna().unique(),
            )
            ph = history_df[
                history_df["name"] == player
            ].sort_values("timestamp")
            st.line_chart(
                ph.set_index("timestamp")["score"],
                use_container_width=True,
            )

with accuracy_tab:
    if results_df.empty:
        st.info("Brak results.csv. Moduł ruszy po zapisaniu typów.")
    else:
        st.dataframe(
            results_df,
            use_container_width=True,
            hide_index=True,
        )

        graded = (
            results_df.dropna(subset=["actual_pra"])
            if "actual_pra" in results_df.columns
            else pd.DataFrame()
        )

        if not graded.empty and "result" in graded.columns:
            total = len(graded)
            wins = int((graded["result"] == "WIN").sum())
            accuracy = wins / total * 100
            profit = (
                graded["profit"].sum()
                if "profit" in graded.columns
                else 0
            )
            roi = profit / total * 100

            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Accuracy", f"{accuracy:.1f}%")
            g2.metric("Graded Picks", total)
            g3.metric("Profit", f"{profit:.2f} u")
            g4.metric("ROI", f"{roi:.1f}%")
        else:
            st.info("Dodaj actual_pra, aby policzyć skuteczność.")
