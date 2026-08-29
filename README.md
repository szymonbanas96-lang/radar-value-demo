# Radar Value v0.8.1 — Live Rosters + Points Radar v1

This version merges the v0.8 app with the first historical Points Radar model.

## Included
- preseason schedule
- Radar Value logo
- Top 3 Value — Today
- Top Value per game
- automatic team rosters
- injury / availability badges
- automatic refresh every 10 minutes
- manual live-data refresh
- Market Scanner
- Line Lab
- Points Radar v1
- leak-safe historical backtest
- unified `requirements.txt`

## New Points Radar files
- `points_radar.py`
- `nba_data_service.py`
- `backtest_points.py`

## Historical test

Install dependencies:

```powershell
pip install -r requirements.txt
```

Run:

```powershell
python backtest_points.py --player "Jalen Brunson" --season "2025-26"
```

The script saves `points_backtest.csv` and reports:
- MAE
- RMSE
- bias
- percentage within ±3 points
- percentage within ±5 points

## Important
Do not judge betting value yet. v1 validates projection quality first.
Historical sportsbook lines will be connected after the baseline model is tested.
