# Radar Value — Stage 2: Historical Points Value Backtest

This package connects the current champion projection model (Points Radar v2.1)
to historical sportsbook POINTS lines.

## Important provider limitation

SportsGameOdds documents historical opening/closing odds on the Pro plan and
above. Historical availability can vary by plan, date, market, and bookmaker.

The script requests:
- finalized NBA events
- `includeOpenCloseOdds=true`
- full-game player POINTS over/under
- opening and closing line per bookmaker

## API key

PowerShell:

```powershell
$env:SPORTSGAMEODDS_API_KEY="YOUR_KEY"
```

## Run

Example:

```powershell
pip install -r requirements.txt

python points_value_backtest.py `
  --season "2025-26" `
  --starts-after "2025-10-20T00:00:00Z" `
  --starts-before "2026-04-20T00:00:00Z" `
  --line-type close
```

Optional single book:

```powershell
python points_value_backtest.py `
  --season "2025-26" `
  --starts-after "2025-10-20T00:00:00Z" `
  --starts-before "2026-04-20T00:00:00Z" `
  --bookmaker draftkings `
  --line-type close
```

## What matters

The script reports win rate by absolute projection edge:

- 0–1
- 1–2
- 2–3
- 3–4
- 4+

and thresholds:

- Edge >= 1
- >= 1.5
- >= 2
- >= 2.5
- >= 3
- >= 3.5
- >= 4
- >= 5

This is the first backtest that directly tests the Radar Value hypothesis:
does a larger projection-vs-book line gap correspond to a higher hit rate?

## Note

This package grades a simple OVER when projection > line and UNDER when
projection < line. It does not yet calculate ROI from American/decimal prices.
That should be the next layer after we confirm a useful win-rate/edge relationship.


## RATE LIMIT FIX

This version handles SportsGameOdds HTTP 429 automatically:
- waits and retries with backoff,
- respects `Retry-After` when provided,
- prints page progress,
- caches Points Radar projections in `points_projections_<season>.csv`.

This means if the odds API rate-limits again, you do not need to recalculate all
30 players on the next run.
