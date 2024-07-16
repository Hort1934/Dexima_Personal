from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class Fields:
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
