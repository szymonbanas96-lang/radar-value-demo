# Radar Value v0.8 — Live Rosters & Availability

New in v0.8:
- live team rosters under each matchup
- player availability badges: OUT / DOUBTFUL / QUESTIONABLE / PROBABLE / DAY-TO-DAY / AVAILABLE
- automatic refresh every 10 minutes
- manual "Refresh live data" button
- 10-minute Streamlit cache to avoid hammering external feeds
- roster feed failure is handled safely: the app keeps running and shows a placeholder
- v0.7 layout, Top 3 Value, Top Value per game, logo, Market Scanner and Line Lab retained

Important:
- Availability depends on what the live source currently publishes.
- Official NBA injury reporting is updated throughout game day; later Radar versions can use status changes as model inputs.
- v0.8 displays the statuses. It does not yet recalculate teammate minutes/usage after an OUT — that is the next model layer.
