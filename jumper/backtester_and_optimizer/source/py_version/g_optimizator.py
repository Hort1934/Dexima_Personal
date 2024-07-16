from dataclasses import dataclass
from typing import Optional, Union
from itertools import product

import pandas as pd

from source.py_version.g_backtester import Backter


@dataclass
class Fields:
    # only_buy: Optional[bool] = False
    # timeframe: list = field(  # don't change!!!
    #     default_factory=lambda: ["1s", "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"]
    # )
    long_entry_sum_in_dollars: Optional[int] = 500
    short_entry_sum_in_dollars: Optional[int] = 500
    long_take_profit_percent: Optional[int] = 50
    long_stop_loss_percent: Optional[int] = 5
    short_take_profit_percent: Optional[int] = 50
    short_stop_loss_percent: Optional[int] = 5
    price_difference_long_entry: Optional[float] = 0.1
    price_difference_short_entry: Optional[float] = 0.1
    block_long_trade_until: Optional[Union[int, None]] = None  # don't change!!!
    block_short_trade_until: Optional[Union[int, None]] = None  # don't change!!!
    long_pause_after_trade_min: Optional[int] = 1
    short_pause_after_trade_min: Optional[int] = 1
    order_expiration_by_price_percent_limit: Optional[int] = 5

    long_period: Optional[int] = 5
    short_period: Optional[int] = 2
    time_ago: Optional[int] = 5
    LEVERAGE: Optional[int] = 10
    long_trailing_stop: Optional[float] = 0.1
    short_trailing_stop: Optional[float] = 0.1


class FieldsGenerator:
    def __init__(self, custom_ranges):
        self.custom_ranges = custom_ranges

    @staticmethod
    def frange(start, stop, step):
        while start < stop:
            yield start
            start += step

    @property
    def combinations(self):
        keys = list(self.custom_ranges.keys())
        values = []

        for key, value in self.custom_ranges.items():
            if isinstance(value, dict):  # если значение является диапазоном
                start = value.get("from", 0)
                stop = value.get("to", 0) + 1
                step = value.get("step", 1)
                values.append(list(self.frange(start, stop, step)))
            else:  # если значение одиночное
                values.append([value])

        for combination in product(*values):
            yield Fields(**dict(zip(keys, combination)))


class Optimizer:

    def __init__(
            self, dataframe, ranges, available_balance, param_to_optimize="start_capital"
    ):
        self.param_to_optimize = param_to_optimize
        self.data = dataframe
        self.ranges = FieldsGenerator(ranges)
        self.result = []
        self.available_balance = available_balance

    def execute(self):
        for combination in self.ranges.combinations:
            b = Backter(
                data=self.data,
                fields=combination,
                available_balance=self.available_balance,
            )
            b.run()
            self.result.append(
                {
                    "fields": combination,
                    "start_capital": b.start_capital,
                    "trades": b.trades,
                }
            )

            # print(f"{b.start_capital=}")
        return self.get_best_combination()

    def get_best_combination(self, ascending=False):
        self.result.sort(
            key=lambda x: x.get(self.param_to_optimize),
            reverse=True if not ascending else False,
        )
        return self.result[0] if self.result else []


if __name__ == "__main__":
    # usage example
    data = pd.read_csv("candle_data.csv")[::-1]
    data.index = data.reset_index().index

    custom_ranges = {
        "long_entry_sum_in_dollars": {"from": 30, "to": 32, "step": 2},
        "time_format": "sec",
        # "short_entry_sum_in_dollars": {"from": 2, "to": 4},
        # "long_take_profit_percent": {"from": 3, "to": 4},
        "time_ago": {"from": 30, "to": 35, "step": 5},
    }

    optimizator = Optimizer(data, custom_ranges)
    # print(optimizator.execute())
