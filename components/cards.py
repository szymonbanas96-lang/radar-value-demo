from html import escape
import pandas as pd
import streamlit as st

def _number(value, fallback=0.0) -> float:
    try:
        if pd.isna(value):
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback

def _text(value, fallback="—") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    value = str(value)
    return value if value.strip() else fallback

def render_top_pick(row: pd.Series) -> None:
    name = escape(_text(row.get("name"), "Unknown player"))
    score = max(0.0, min(100.0, _number(row.get("score"))))
    signal = escape(_text(row.get("signal")))
    edge = _number(row.get("real_edge", row.get("edge", 0)))
    line = _number(row.get("book_line", 0))
    pra5 = _number(row.get("pra5", 0))

    st.markdown(
        f"""
        <div class="rv-top-card">
            <div class="rv-top-label">Today's best value</div>
            <div class="rv-top-name">{name}</div>
            <div class="rv-top-signal">{signal}</div>

            <div class="rv-score-row">
                <div>
                    <div class="rv-score">{score:.1f}</div>
                    <div class="rv-score-caption">Radar Score / 100</div>
                </div>
                <div style="flex:1; max-width:360px;">
                    <div class="rv-score-caption">Model strength</div>
                    <div class="rv-progress"><span style="width:{score:.0f}%"></span></div>
                </div>
            </div>

            <div class="rv-card-data" style="max-width:520px;">
                <div>
                    <div class="rv-card-data-label">Real edge</div>
                    <div class="rv-card-data-value">{edge:+.1f}</div>
                </div>
                <div>
                    <div class="rv-card-data-label">Book line</div>
                    <div class="rv-card-data-value">{line:.1f}</div>
                </div>
                <div>
                    <div class="rv-card-data-label">PRA last 5</div>
                    <div class="rv-card-data-value">{pra5:.1f}</div>
                </div>
                <div>
                    <div class="rv-card-data-label">Status</div>
                    <div class="rv-card-data-value">Active signal</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_metrics(df: pd.DataFrame) -> None:
    avg_score = _number(df["score"].mean()) if "score" in df else 0
    elite = int(df["elite_play"].fillna(False).astype(bool).sum()) if "elite_play" in df else 0
    strong = int((df["signal"] == "🔥 STRONG OVER TREND").sum()) if "signal" in df else 0
    tracked = len(df)

    st.markdown(
        f"""
        <div class="rv-metrics-grid">
            <div class="rv-metric">
                <div class="rv-metric-label">Average Radar Score</div>
                <div class="rv-metric-value">{avg_score:.1f}</div>
                <div class="rv-metric-detail">Today's model output</div>
            </div>
            <div class="rv-metric">
                <div class="rv-metric-label">Elite Plays</div>
                <div class="rv-metric-value">{elite}</div>
                <div class="rv-metric-detail">Highest confidence tier</div>
            </div>
            <div class="rv-metric">
                <div class="rv-metric-label">Strong Over Trends</div>
                <div class="rv-metric-value">{strong}</div>
                <div class="rv-metric-detail">Positive market signals</div>
            </div>
            <div class="rv-metric">
                <div class="rv-metric-label">Players Tracked</div>
                <div class="rv-metric-value">{tracked}</div>
                <div class="rv-metric-detail">Current radar pool</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def render_player_cards(df: pd.DataFrame, limit: int = 9) -> None:
    if df.empty:
        st.info("Brak zawodników spełniających wybrane filtry.")
        return

    cards = []
    for _, row in df.head(limit).iterrows():
        name = escape(_text(row.get("name"), "Unknown player"))
        score = _number(row.get("score"))
        signal = escape(_text(row.get("signal")))
        edge = _number(row.get("real_edge", row.get("edge", 0)))
        line = _number(row.get("book_line", 0))
        pra5 = _number(row.get("pra5", 0))
        minutes = _number(row.get("minutes_trend", 0))

        cards.append(
            f"""
            <article class="rv-player-card">
                <div class="rv-player-head">
                    <div class="rv-player-name">{name}</div>
                    <span class="rv-badge">{signal}</span>
                </div>
                <div class="rv-card-score">{score:.1f} <small>/ 100</small></div>
                <div class="rv-progress"><span style="width:{max(0, min(100, score)):.0f}%"></span></div>
                <div class="rv-card-data">
                    <div>
                        <div class="rv-card-data-label">Real edge</div>
                        <div class="rv-card-data-value">{edge:+.1f}</div>
                    </div>
                    <div>
                        <div class="rv-card-data-label">Book line</div>
                        <div class="rv-card-data-value">{line:.1f}</div>
                    </div>
                    <div>
                        <div class="rv-card-data-label">PRA last 5</div>
                        <div class="rv-card-data-value">{pra5:.1f}</div>
                    </div>
                    <div>
                        <div class="rv-card-data-label">Minutes trend</div>
                        <div class="rv-card-data-value">{minutes:+.1f}</div>
                    </div>
                </div>
            </article>
            """
        )

    st.markdown(
        '<div class="rv-player-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )
