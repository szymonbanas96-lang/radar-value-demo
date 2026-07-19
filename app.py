import subprocess
import sys
import streamlit as st
import pandas as pd
import os

st.set_page_config(
    page_title="Radar Value 2.0",
    layout="wide"
)

if os.path.exists("history.csv"):
    history_df = pd.read_csv("history.csv")
else:
    history_df = pd.DataFrame()

if os.path.exists("results.csv"):
    results_df = pd.read_csv("results.csv")
else:
    results_df = pd.DataFrame()

    # auto grading
if not results_df.empty:

    def calculate_result(row):

        if pd.isna(row["actual_pra"]):
            return ""

        if row["prediction"] == "OVER":

            if row["actual_pra"] > row["book_line"]:
                return "WIN"
            else:
                return "LOSS"

        elif row["prediction"] == "UNDER":

            if row["actual_pra"] < row["book_line"]:
                return "WIN"
            else:
                return "LOSS"

        return ""

    results_df["result"] = results_df.apply(
        calculate_result,
        axis=1
    )

# profit calculation
if not results_df.empty:

    def calculate_profit(row):

        if row["result"] == "WIN":
            return row["odds"] - 1

        elif row["result"] == "LOSS":
            return -1

        return 0

    results_df["profit"] = results_df.apply(
        calculate_profit,
        axis=1
    )
st.title("🔥 Radar Value 2.0")

if st.button("🔄 Refresh Radar"):
    with st.spinner("Radar pobiera i analizuje dane..."):
        result = subprocess.run(
            [sys.executable, "main.py"],
            capture_output=True,
            text=True
        )

    if result.returncode == 0:
        st.success("Radar updated!")
        st.rerun()
    else:
        st.error("Nie udało się odświeżyć Radaru.")
        st.code(result.stderr)
df = pd.read_csv("radar_results.csv")
df = df.sort_values(by="score", ascending=False)

top_pick = df.iloc[0]

elite_df = df[df["elite_play"] == True]

if not elite_df.empty:

    st.subheader("🚨 ELITE PLAYS")

    st.dataframe(
        elite_df,
        use_container_width=True
    )

st.subheader("🏆 TOP RADAR PICK")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Player", top_pick["name"])

with col2:
    st.metric("Radar Score", top_pick["score"])

with col3:
    st.metric("Signal", top_pick["signal"])

st.divider()

st.subheader("📈 RADAR STATS")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Average Radar Score", round(df["score"].mean(), 1))

with col2:
    st.metric(
        "Strong Over Trends",
        len(df[df["signal"] == "🔥 STRONG OVER TREND"])
    )

with col3:
    st.metric(
        "Cold Trends",
        len(df[df["signal"] == "🔻 COLD TREND"])
    )

st.divider()

strong_over = df[df["signal"] == "🔥 STRONG OVER TREND"]
over_trend = df[df["signal"] == "⚠️ OVER TREND"]
cold_trend = df[df["signal"] == "🔻 COLD TREND"]

st.subheader("🔥 STRONG OVER TRENDS")
st.dataframe(strong_over, use_container_width=True)

st.subheader("⚠️ OVER TRENDS")
st.dataframe(over_trend, use_container_width=True)

st.subheader("🔻 COLD TRENDS")
st.dataframe(cold_trend, use_container_width=True)

st.divider()

st.subheader("🎯 RADAR FILTERS")

col1, col2, col3 = st.columns(3)

with col1:
    selected_signals = st.multiselect(
        "Signals",
        options=df["signal"].unique(),
        default=df["signal"].unique()
    )

with col2:
    min_score = st.slider(
        "Minimum Radar Score",
        0,
        100,
        20
    )

with col3:
    min_edge = st.slider(
        "Minimum Real Edge",
        -10.0,
        10.0,
        0.0
    )

filtered_df = df[
    (df["signal"].isin(selected_signals))
    & (df["score"] >= min_score)
    & (df["real_edge"] >= min_edge)
]

st.subheader("📊 DAILY RADAR RESULTS")
st.dataframe(filtered_df, use_container_width=True)

st.divider()

st.subheader("📜 RADAR HISTORY")

if history_df.empty:
    st.info("Brak historii. Kliknij Refresh Radar albo odpal py main.py.")
elif "timestamp" not in history_df.columns:
    st.warning("Historia istnieje, ale nie ma jeszcze kolumny timestamp. Odpal ponownie Refresh Radar.")
    st.dataframe(history_df, use_container_width=True)
else:
    history_sorted = history_df.sort_values(
        by="timestamp",
        ascending=False
    )
    st.dataframe(history_sorted, use_container_width=True)

st.divider()

st.subheader("📈 RADAR SCORE HISTORY")

if not history_df.empty and "timestamp" in history_df.columns:
    selected_player = st.selectbox(
        "Select Player",
        history_df["name"].unique()
    )

    player_history = history_df[
        history_df["name"] == selected_player
    ].sort_values(by="timestamp")

    st.line_chart(
        player_history.set_index("timestamp")["score"]
    )
else:
    st.info("Brak danych historycznych do wykresu.")

st.divider()

st.subheader("✅ ACCURACY TRACKING")

if results_df.empty:
    st.info("Brak pliku results.csv.")
else:
    st.dataframe(results_df, use_container_width=True)

    graded = results_df.dropna(subset=["actual_pra"])

    if not graded.empty:
        total = len(graded)
        wins = len(graded[graded["result"] == "WIN"])
        accuracy = wins / total * 100

        profit = graded["profit"].sum()
        roi = (profit / total) * 100

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Accuracy", f"{round(accuracy, 1)}%")

        with col2:
            st.metric("Graded Picks", total)

        with col3:
            st.metric("Wins", wins)

        with col4:
            st.metric("Profit (Units)", round(profit, 2))

        with col5:
            st.metric("ROI %", f"{round(roi,1)}%")
    else:
        st.info("Dodaj actual_pra po meczach, żeby liczyć skuteczność.")