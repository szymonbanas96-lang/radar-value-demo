# Radar Value — Preseason 2026

## Included
- Preseason 2026 home page
- Automatic schedule feed with fallback
- Team/date filters
- Four Radar sections: Points, Assists, Rebounds, PRA
- Market Scanner shell
- Interactive bookmaker-line slider
- Game 7 removed
- Readiness/status screen

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud
Put `app.py`, `schedule_service.py`, and `requirements.txt` in the repository root.
Set the main file to `app.py`.

## Next integrations
1. Odds API for player props
2. Player projections / Radar models
3. Injury and availability feed
4. Live line movement and Market Lag
5. Replace demo slider data with the selected live scanner result

The current Line Lab values are UI-demo values, not betting predictions.
