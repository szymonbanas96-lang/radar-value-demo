from dataclasses import dataclass, asdict
from typing import List, Optional
import pandas as pd


@dataclass
class PointsProjectionV2:
    player: str
    projection: float
    model_score: int
    games_used: int
    pts_l5: float
    pts_l10: float
    pts_l20: float
    minutes_l5: float
    minutes_l10: float
    fga_l5: float
    fga_l10: float
    baseline: float
    form_adjustment: float
    volume_adjustment: float
    location_adjustment: float
    rest_adjustment: float
    defense_adjustment: float
    pace_adjustment: float

    def to_dict(self):
        return asdict(self)


class PointsRadarV2:
    """
    v2 changes:
    - stronger regression to a stable 20-game baseline
    - L5 is a signal, not the main forecast
    - recent-form adjustment is capped
    - defense + pace are explicit optional pre-game inputs

    IMPORTANT: every input used for a historical target must be known before tipoff.
    """

    MIN_HISTORY = 10

    @staticmethod
    def _avg(series) -> float:
        s = pd.to_numeric(series, errors="coerce").dropna()
        return float(s.mean()) if len(s) else 0.0

    def project(
        self,
        player: str,
        history: pd.DataFrame,
        target_is_home: Optional[bool] = None,
        opponent_points_factor: float = 1.0,
        pace_factor: float = 1.0,
        days_rest: Optional[int] = None,
    ) -> PointsProjectionV2:
        required = {"GAME_DATE", "PTS", "MIN", "FGA", "FTA", "FG3A", "MATCHUP"}
        missing = required - set(history.columns)
        if missing:
            raise ValueError(f"Missing columns: {sorted(missing)}")

        h = history.copy()
        h["GAME_DATE"] = pd.to_datetime(h["GAME_DATE"])
        h = h.sort_values("GAME_DATE", ascending=False).reset_index(drop=True)
        if len(h) < self.MIN_HISTORY:
            raise ValueError(f"{player}: need at least {self.MIN_HISTORY} prior games")

        l5, l10, l20 = h.head(5), h.head(10), h.head(20)

        pts5 = self._avg(l5["PTS"])
        pts10 = self._avg(l10["PTS"])
        pts20 = self._avg(l20["PTS"])

        min5 = self._avg(l5["MIN"])
        min10 = self._avg(l10["MIN"])
        fga5 = self._avg(l5["FGA"])
        fga10 = self._avg(l10["FGA"])
        fta5 = self._avg(l5["FTA"])
        fta10 = self._avg(l10["FTA"])

        # Stable anchor. The old model put 55% directly on L5.
        baseline = 0.15 * pts5 + 0.35 * pts10 + 0.50 * pts20

        # Regression-aware form: hot/cold L5 only nudges the forecast.
        form_gap = pts5 - pts20
        form_adjustment = max(-1.25, min(1.25, form_gap * 0.12))

        # Role/volume proxy, intentionally conservative until usage is added.
        min_delta = min5 - min10
        shot_delta = (fga5 - fga10) + 0.44 * (fta5 - fta10)
        volume_adjustment = (
            max(-0.75, min(0.75, min_delta * 0.12))
            + max(-0.75, min(0.75, shot_delta * 0.12))
        )

        location_adjustment = 0.0
        if target_is_home is not None:
            is_home = ~h["MATCHUP"].astype(str).str.contains("@", regex=False)
            split = h[is_home == target_is_home].head(20)
            if len(split) >= 5:
                split_avg = self._avg(split["PTS"])
                overall = self._avg(h.head(20)["PTS"])
                location_adjustment = max(-0.75, min(0.75, (split_avg - overall) * 0.15))

        rest_adjustment = 0.0
        if days_rest is not None:
            if days_rest <= 0:
                rest_adjustment = -0.35
            elif days_rest >= 3:
                rest_adjustment = 0.20

        # Factors are multiplicative context around neutral 1.00.
        # Caps prevent one noisy team metric from hijacking a projection.
        opponent_points_factor = max(0.94, min(1.06, float(opponent_points_factor)))
        pace_factor = max(0.96, min(1.04, float(pace_factor)))
        defense_adjustment = baseline * (opponent_points_factor - 1.0) * 0.65
        pace_adjustment = baseline * (pace_factor - 1.0) * 0.55

        projection = (
            baseline + form_adjustment + volume_adjustment + location_adjustment
            + rest_adjustment + defense_adjustment + pace_adjustment
        )
        projection = round(max(0.0, projection), 1)

        # Confidence is intentionally modest in v2. It is NOT Radar Value.
        pts_std = pd.to_numeric(l20["PTS"], errors="coerce").std(ddof=0)
        min_std = pd.to_numeric(l20["MIN"], errors="coerce").std(ddof=0)
        sample_score = min(30, len(h))
        stability = max(0, 45 - int((pts_std or 0) * 2.2))
        minutes_stability = max(0, 25 - int((min_std or 0) * 2.0))
        model_score = max(1, min(100, sample_score + stability + minutes_stability))

        return PointsProjectionV2(
            player=player, projection=projection, model_score=model_score,
            games_used=len(h), pts_l5=round(pts5,1), pts_l10=round(pts10,1),
            pts_l20=round(pts20,1), minutes_l5=round(min5,1),
            minutes_l10=round(min10,1), fga_l5=round(fga5,1),
            fga_l10=round(fga10,1), baseline=round(baseline,2),
            form_adjustment=round(form_adjustment,2),
            volume_adjustment=round(volume_adjustment,2),
            location_adjustment=round(location_adjustment,2),
            rest_adjustment=round(rest_adjustment,2),
            defense_adjustment=round(defense_adjustment,2),
            pace_adjustment=round(pace_adjustment,2),
        )
