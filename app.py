import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

from components.cards import render_metrics, render_player_cards, render_top_pick
from components.data import grade_results, load_data
from components.header import render_header, render_section
from components.theme import load_theme

ROOT = Path(__file__).resolve().parent
FAVICON = ROOT / "assets" / "favicon.png"

st.set_page_config(
    page_title="Radar Value",
    page_icon=str(FAVICON) if FAVICON.exists() else "📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

load_theme()
render_header()

radar_df, history_df, results_df = load_data()
results_df = grade_results(results_df)

refresh_col, info_col = st.columns([1, 4])

with refresh_col:
    refresh_clicked = st.button("📡 Scan Radar", use_container_width=True)

with info_col:
    st.caption(
        "Demo v0.2 · Dane są ładowane z radar_results.csv. "
        "Przycisk skanu uruchamia main.py na serwerze."
    )

if refresh_clicked:
    with st.status("📡 Scanning today's games...", expanded=True) as status:
        st.write("🏀 Loading players and rotations...")
        result = subprocess.run(
            [sys.executable, str(ROOT / "main.py")],
            capture_output=True,
            text=True,
            cwd=ROOT,
        )
        st.write("📈 Calculating Radar Score...")

        if result.returncode == 0:
            status.update(label="✅ Radar ready", state="complete")
            st.rerun()
        else:
            status.update(label="❌ Radar scan failed", state="error")
            st.code(result.stderr or result.stdout or "Brak dodatkowych informacji.")

if radar_df.empty:
    st.error(
        "Nie udało się wczytać radar_results.csv. "
        "Sprawdź, czy plik znajduje się obok app.py."
    )
    st.stop()

required = {"name", "score", "signal"}
missing = required.difference(radar_df.columns)
if missing:
    st.error("W radar_results.csv brakuje kolumn: " + ", ".join(sorted(missing)))
    st.stop()

radar_df = radar_df.copy()
radar_df["score"] = pd.to_numeric(radar_df["score"], errors="coerce").fillna(0)
radar_df = radar_df.sort_values("score", ascending=False)
top_pick = radar_df.iloc[0]

render_section("Daily intelligence", "Top Radar Pick")
render_top_pick(top_pick)

render_section("Market overview", "Radar Snapshot")
render_metrics(radar_df)

render_section("Signal explorer", "Today's Player Cards")

filter_col1, filter_col2, filter_col3 = st.columns(3)

with filter_col1:
    signals = list(radar_df["signal"].dropna().unique())
    selected_signals = st.multiselect(
        "Signals",
        options=signals,
        default=signals,
    )

with filter_col2:
    min_score = st.slider(
        "Minimum Radar Score",
        min_value=0,
        max_value=100,
        value=20,
    )

edge_column = "real_edge" if "real_edge" in radar_df.columns else "edge"

with filter_col3:
    min_edge = st.slider(
        "Minimum Edge",
        min_value=-15.0,
        max_value=15.0,
        value=0.0,
        step=0.5,
    )

filtered_df = radar_df[
    radar_df["signal"].isin(selected_signals)
    & (radar_df["score"] >= min_score)
].copy()

if edge_column in filtered_df.columns:
    filtered_df[edge_column] = pd.to_numeric(
        filtered_df[edge_column],
        errors="coerce",
    ).fillna(0)
    filtered_df = filtered_df[filtered_df[edge_column] >= min_edge]

render_player_cards(filtered_df, limit=12)

with st.expander("View complete radar table"):
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)

render_section("Performance", "History & Accuracy")

history_tab, accuracy_tab = st.tabs(["Radar history", "Accuracy tracking"])

with history_tab:
    if history_df.empty:
        st.info("Brak history.csv. Pojawi się po zapisaniu pierwszych skanów.")
    else:
        if "timestamp" in history_df.columns:
            history_df = history_df.sort_values("timestamp", ascending=False)
        st.dataframe(history_df, use_container_width=True, hide_index=True)

        if {"timestamp", "name", "score"}.issubset(history_df.columns):
            player = st.selectbox(
                "Player score history",
                options=history_df["name"].dropna().unique(),
            )
            player_history = history_df[
                history_df["name"] == player
            ].sort_values("timestamp")
            st.line_chart(
                player_history.set_index("timestamp")["score"],
                use_container_width=True,
            )

with accuracy_tab:
    if results_df.empty:
        st.info("Brak results.csv. Moduł zacznie działać po zapisaniu typów.")
    else:
        st.dataframe(results_df, use_container_width=True, hide_index=True)

        if "actual_pra" in results_df.columns:
            graded = results_df.dropna(subset=["actual_pra"])
        else:
            graded = pd.DataFrame()

        if not graded.empty and "result" in graded.columns:
            total = len(graded)
            wins = int((graded["result"] == "WIN").sum())
            accuracy = wins / total * 100
            profit = graded["profit"].sum() if "profit" in graded.columns else 0
            roi = profit / total * 100

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Accuracy", f"{accuracy:.1f}%")
            c2.metric("Graded picks", total)
            c3.metric("Profit", f"{profit:.2f} u")
            c4.metric("ROI", f"{roi:.1f}%")
        else:
            st.info("Dodaj actual_pra po meczach, aby liczyć skuteczność.")
