# Radar Value — Odds Fetcher v0.1

This module pulls current NBA player-prop lines for:

- Points (PTS)
- Assists (AST)
- Rebounds (REB)

Provider: SportsGameOdds.

It stores every bookmaker line separately and also creates a median market
consensus line for each player/market/game.

## 1. Get API key

Create an API key at SportsGameOdds. The free Amateur tier is enough to test
the integration.

Do not paste the key directly into `odds_service.py`.

## 2. Windows PowerShell

For the current PowerShell window:

```powershell
$env:SPORTSGAMEODDS_API_KEY="YOUR_KEY"
python test_odds.py
```

Or to run the full exporter:

```powershell
python odds_service.py
```

It creates:

- `nba_props_raw.csv`
- `nba_props_consensus.csv`

## 3. Later Streamlit integration

Import:

```python
from odds_service import fetch_nba_player_props, build_consensus_lines
```

Then:

```python
props = fetch_nba_player_props()
consensus = build_consensus_lines(props)
```

The next Radar Value step is to merge `consensus_line` with the model's own
PTS / AST / REB projection and calculate:

`edge = radar_projection - consensus_line`

Important: these are sportsbook market lines, not NBA league-issued lines.
The NBA does not publish an "official betting line"; the API aggregates
sportsbook prices.
