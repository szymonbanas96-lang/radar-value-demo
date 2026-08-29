# Radar Value — Points Radar v1

First isolated model for Radar Value.

## What v1 uses
- PTS last 5
- PTS last 10
- minutes trend
- FGA trend
- FTA trend
- 3PA stored for diagnostics
- home/away split
- rest days
- optional opponent defensive factor

The first backtest deliberately leaves opponent factor neutral. We first need
to measure whether the basic player-form/role model works before adding more
variables.

## Anti-leak rule

For a historical game on date X, the model receives only rows dated before X.
The actual result of X is revealed only after the projection is produced.

This is the most important rule in the project.

## Run first test

Install:

```powershell
pip install -r requirements.txt
```

Example:

```powershell
python backtest_points.py --player "Jalen Brunson" --season "2025-26"
```

Output:
- MAE
- RMSE
- bias
- % predictions within 3 points
- % predictions within 5 points
- `points_backtest.csv` with every historical projection

You can also test a local NBA-style player game-log CSV:

```powershell
python backtest_points.py --player "Jalen Brunson" --csv brunson.csv
```

Required CSV columns:
`GAME_DATE, PTS, MIN, FGA, FTA, FG3A, MATCHUP`

## Next iteration after results

Do NOT add every feature immediately. Run v1 first. Then we compare misses and
add one layer at a time:
1. opponent defense / pace
2. starter & role changes
3. teammate OUT impact
4. usage
5. historical sportsbook line / Radar Value
