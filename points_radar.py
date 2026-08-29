from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import math
import pandas as pd


@dataclass
class PointsProjection:
    player: str
    projection: float
    model_score: int
    games_used: int
    pts_l5: float
    pts_l10: float
    minutes_l5: float
    minutes_l10: float
    fga_l5: float
    fta_l5: float
    three_pa_l5: float
    home_away_avg: Optional[float]
    opponent_adjustment: float
    rest_adjustment: float
    trend_adjustment: float

    def to_dict(self):
        return asdict(self)


class PointsRadarV1:
    """
    Leak-safe baseline Points model.

    IMPORTANT:
    The input history must contain ONLY games played BEFORE the target game.
    v1 intentionally starts simple so that every later feature can be
    backtested and measured instead of being added by intuition alone.
    """

    MIN_HISTORY = 5

    @staticmethod
    def _weighted(values: List[float]) -> float:
        vals = [float(v) for v in values if pd.notna(v)]
        if not vals:
            return 0.0
        # Most recent game should be first.
        weights = list(range(len(vals), 0, -1))
        return sum(v * w for v, w in zip(vals, weights)) / sum(weights)

    @staticmethod
    def _avg(series) -> float:
        s = pd.to_numeric(series, errors="coerce").dropna()
        return float(s.mean()) if len(s) else 0.0

    def project(
        self,
        player: str,
        history: pd.DataFrame,
        target_is_home: Optional[bool] = None,
        opponent_def_factor: float = 1.0,
        days_rest: Optional[int] = None,
    ) -> PointsProjection:
        required = {"GAME_DATE", "PTS", "MIN", "FGA", "FTA", "FG3A", "MATCHUP"}
        missing = required - set(history.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        h = history.copy()
        h["GAME_DATE"] = pd.to_datetime(h["GAME_DATE"])
        h = h.sort_values("GAME_DATE", ascending=False).reset_index(drop=True)

        if len(h) < self.MIN_HISTORY:
            raise ValueError(f"{player}: need at least {self.MIN_HISTORY} prior games")

        l5 = h.head(5)
        l10 = h.head(10)

        pts_l5 = self._avg(l5["PTS"])
        pts_l10 = self._avg(l10["PTS"])
        min_l5 = self._avg(l5["MIN"])
        min_l10 = self._avg(l10["MIN"])
        fga_l5 = self._avg(l5["FGA"])
        fta_l5 = self._avg(l5["FTA"])
        fg3a_l5 = self._avg(l5["FG3A"])

        # Core scoring baseline: recent production + slightly more stable 10-game form.
        baseline = 0.55 * pts_l5 + 0.45 * pts_l10

        # Minutes trend: scale conservatively, capped to avoid overreaction.
        min_delta = min_l5 - min_l10
        trend_adjustment = max(-2.0, min(2.0, min_delta * 0.28))

        # Shot-volume trend vs 10-game baseline.
        fga_l10 = self._avg(l10["FGA"])
        fta_l10 = self._avg(l10["FTA"])
        volume_delta = (fga_l5 - fga_l10) + 0.44 * (fta_l5 - fta_l10)
        volume_adjustment = max(-2.0, min(2.0, volume_delta * 0.30))

        # Home/away split from prior games only. Keep it as a small adjustment.
        split_avg = None
        location_adjustment = 0.0
        if target_is_home is not None:
            is_home = ~h["MATCHUP"].astype(str).str.contains("@", regex=False)
            split = h[is_home == target_is_home].head(15)
            if len(split) >= 3:
                split_avg = self._avg(split["PTS"])
                overall = self._avg(h.head(15)["PTS"])
                location_adjustment = max(-1.25, min(1.25, (split_avg - overall) * 0.25))

        # opponent_def_factor: 1.00 neutral; 0.95 difficult; 1.05 favorable.
        opponent_def_factor = max(0.90, min(1.10, float(opponent_def_factor)))
        opponent_adjustment = baseline * (opponent_def_factor - 1.0)

        # Small rest factor; no fabricated injury/role information in v1.
        rest_adjustment = 0.0
        if days_rest is not None:
            if days_rest <= 0:
                rest_adjustment = -0.6
            elif days_rest >= 3:
                rest_adjustment = 0.35

        projection = (
            baseline
            + trend_adjustment
            + volume_adjustment
            + location_adjustment
            + opponent_adjustment
            + rest_adjustment
        )
        projection = round(max(0.0, projection), 1)

        # Model Score = confidence in the projection, NOT betting value.
        games_score = min(30, len(h) * 2)
        minutes_stability = max(0, 25 - int(pd.to_numeric(l10["MIN"], errors="coerce").std(ddof=0) * 3))
        scoring_stability = max(0, 25 - int(pd.to_numeric(l10["PTS"], errors="coerce").std(ddof=0) * 1.5))
        role_signal = min(20, int(abs(min_delta) * 3 + abs(volume_delta) * 2))
        model_score = max(1, min(100, games_score + minutes_stability + scoring_stability + role_signal))

        return PointsProjection(
            player=player,
            projection=projection,
            model_score=model_score,
            games_used=len(h),
            pts_l5=round(pts_l5, 1),
            pts_l10=round(pts_l10, 1),
            minutes_l5=round(min_l5, 1),
            minutes_l10=round(min_l10, 1),
            fga_l5=round(fga_l5, 1),
            fta_l5=round(fta_l5, 1),
            three_pa_l5=round(fg3a_l5, 1),
            home_away_avg=round(split_avg, 1) if split_avg is not None else None,
            opponent_adjustment=round(opponent_adjustment, 2),
            rest_adjustment=round(rest_adjustment, 2),
            trend_adjustment=round(trend_adjustment + volume_adjustment + location_adjustment, 2),
        )
