import datetime
import itertools
import random as rnd
from pathlib import Path
from typing import Dict, List, Union
import requests

import pandas as pd
from source.grid_project.src.common.strategy import ExpoGridStrategy
from source.grid_project.src.common.strategy.expo_grid.grid import Grid
from source.grid_project.src.common.strategy.expo_grid.settings import (
    ExpoGridStrategySettings,
)
from source.grid_project.src.database.core import Database, connection
from source.grid_project.src.services.data_loader.typedef import KlineInterval
from source.grid_project.src.services.executor import BacktestExecutor
from source.grid_project.src.utils.logger import Logger


import os


logger = Logger(__name__)


class Optimizer:
    _backtest_params = (
        "Initial balance",
        "Available balance",
        "Profit",
        "Total trades",
        "Long trades",
        "Long TP",
        "Long SL",
        "Short trades",
        "Short TP",
        "Short SL",
        "Fees paid",
    )

    def __init__(
        self, settings: ExpoGridStrategySettings = ExpoGridStrategySettings.from_file()
    ):
        self.settings = settings
        self.param_combinations = self.generate_param_combinations()
        self.results: List[Dict[str, float]] = []
        self._db = Database(connection)

    def get_best_result_by_param(self, param: str) -> Dict[str, float]:
        if param not in self._backtest_params:
            raise ValueError(
                f"Parameter {param} is not valid. Available params:"
                f" {self._backtest_params}"
            )
        if not self.results:
            raise ValueError(
                "Optimizer has no results. You should run optimization before getting"
                " the best result"
            )
        return sorted(self.results, key=lambda x: x[param], reverse=True)[0]

    def generate_param_combinations(self) -> List[Dict[str, Union[str, int, float]]]:
        optimization_settings = self.settings.model_dump().get("optimization", {})
        keys = [k for k in optimization_settings.keys() if k != "timeframe"]
        value_combinations = [optimization_settings[key] for key in keys]
        param_combinations = list(itertools.product(*value_combinations))
        return [
            {keys[i]: combination[i] for i in range(len(keys))}
            for combination in param_combinations
        ]

    async def run_optimization(
        self, from_: datetime.datetime, to: datetime.datetime, backtest_and_optimization_id: int, iterations: int
    ) -> None:
        timeframes: List[KlineInterval] = self.settings.optimization.get(
            "timeframe", []
        )
        for timeframe in timeframes:
            data = self._db.get_historical_data(
                exchange="bybit",
                type_="futures",
                symbol=self.settings.symbol,
                timeframe=timeframe,
                from_=from_,
                to=to,
            )
            counter = 0
            # for combination in self.param_combinations[:iterations]:
            for _ in range(min(iterations, len(self.param_combinations))):
                counter += 1
                if counter % 10 == 0 or counter == 1:
                    print('Left:', len(self.param_combinations) - counter, 'iterations in timeframe:', timeframe)
                    # 60-DataFromOptimizer
                    url = 'http://backend-app/update_optimization_data/'
                    iterations_data = {
                        'backtest_and_optimization_id': backtest_and_optimization_id,
                        'final_progress_number': len(self.param_combinations),
                        'progress': counter
                    }
                    response = requests.get(url, params=iterations_data)
                    if response.status_code == 200:
                        response_result = response.json()
                        # print(response_result)
                    else:
                        print(response.text)
                    # 60-DataFromOptimizer
                combination = rnd.choice(self.param_combinations)
                executor = BacktestExecutor(
                    data=data,
                    initial_balance=self.settings.available_balance,
                )
                async with executor:
                    strategy = ExpoGridStrategy(
                        executor=executor,
                        grid=Grid(),
                        settings=self.settings.model_copy(update=combination),
                    )
                    while executor.is_running:
                        await strategy.execute()

                    result = executor.result()
                    combination.update({"timeframe": timeframe})
                    result.update({"settings": combination})  # type: ignore[dict-item]
                    self.results.append(result)


def save_results(results: List[Dict[str, float]]) -> None:
    df = pd.DataFrame(results)
    df.to_csv(Path(__file__).parent / "optimization_results.csv")


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        o = Optimizer()
        from_ = datetime.datetime(2024, 1, 18)
        to = datetime.datetime(2024, 1, 26)
        await o.run_optimization(from_=from_, to=to)
        print(o.get_best_result_by_param("Profit"))
        save_results(o.results)

    asyncio.run(main())
