from __future__ import annotations

from pathlib import Path
from typing import Any, Type, Union

from source.grid_project.src.common.strategy.base.settings import BaseStrategySettings
from source.grid_project.src.services.data_loader.typedef import (
    KlineInterval,
    LineDistribution,
    Sort,
)


class ExpoGridStrategySettings(BaseStrategySettings):
    symbol: str
    leverage: Union[int, float]
    num_of_grids: int
    available_balance: float
    timeframe: KlineInterval
    price_range: int
    activation_trigger_in_percent: float
    distribution_of_grid_lines: LineDistribution
    line_disbalance_direction: Sort
    short_stop_loss_in_percent: float
    long_stop_loss_in_percent: float
    grid_disbalance_direction: Sort
    trend_period_timeframe: KlineInterval
    trend_period: int
    optimization: dict[str, Any] = {
        "num_of_grids": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        "timeframe": ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"],
        "price_range": [12, 22, 32, 42, 52, 62, 72],
        "activation_trigger_in_percent": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        "distribution_of_grid_lines": ["LINEAR", "FIBONACCI"],
        "line_disbalance_direction": ["ASCENDING", "DESCENDING"],
        "short_stop_loss_in_percent": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        "long_stop_loss_in_percent": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        "grid_disbalance_direction": ["ASCENDING", "DESCENDING"],
        "trend_period_timeframe": ["1m", "1h", "1d"],
        "trend_period": [12, 22, 32, 42, 52, 62, 72],
    }

    @classmethod
    def from_file(
        cls: Type[ExpoGridStrategySettings], cwd: Path = Path(__file__).parent
    ) -> ExpoGridStrategySettings:
        return super().from_file(cwd=cwd)
