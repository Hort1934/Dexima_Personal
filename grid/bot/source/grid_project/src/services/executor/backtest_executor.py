from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from types import TracebackType
from typing import (
    Any,
    Dict,
    Final,
    List,
    Optional,
    Type,
    Union,
)

import pandas as pd

from source.grid_project.src.common.executor.base import AbstractExecutor
from source.grid_project.src.common.typedef import OrderSide, OrderType
from source.grid_project.src.utils.logger import Logger


FEE: Final[float] = 0.01

# FEE: Final[float] = settings.bybit.fee

logger = Logger(__name__)


@dataclass
class Position:
    symbol: str
    side: str
    size: float
    entry_price: float
    take_profit: float
    stop_loss: float

    def get(self, key: str, default_value: Any = None) -> Any:
        return {"side": self.side.title(), "size": self.size}

    @classmethod
    def from_order(cls, order: Order) -> Position:
        return cls(
            symbol=order.symbol,
            side=order.side,
            size=order.amount,
            entry_price=order.price,  # type: ignore
            take_profit=order.take_profit,  # type: ignore
            stop_loss=order.stop_loss,  # type: ignore
        )

    def get_profit(self, close_price: float) -> float:
        if self.side == "buy":
            return (close_price - self.entry_price) * self.size
        return (self.entry_price - close_price) * self.size


@dataclass
class Order:
    symbol: str
    type: OrderType
    side: OrderSide
    amount: float
    price: Optional[float] = None
    params: Optional[Dict[str, Any]] = None
    take_profit: Optional[float] = None
    stop_loss: Optional[float] = None
    order_id: uuid.UUID = field(default_factory=uuid.uuid4)

    def __post_init__(self) -> None:
        if self.params:
            self.take_profit = self.params.get("takeProfit")
            self.stop_loss = self.params.get("stopLoss")

    def get(self, key: str, default_value: Any = None) -> Any:
        return {"orderId": self.order_id}


class BacktestExecutor(AbstractExecutor):
    def __init__(self, data: pd.DataFrame, initial_balance: float) -> None:
        self.data = data
        self.initial_balance = initial_balance

        self.orders: List[Order] = []
        self.position: Optional[Position] = None

        self._index: int = 30
        self._leverage: float = 1.0
        self._available_balance: float = self.initial_balance
        self._fees_paid: float = 0.0
        self._total_trades: int = 0
        self._long_trades: int = 0
        self._long_tp: int = 0
        self._long_sl: int = 0
        self._short_trades: int = 0
        self._short_tp: int = 0
        self._short_sl: int = 0

    @property
    def is_running(self) -> bool:
        return self._index < self.data.shape[0] - 1  # type: ignore

    async def create_order(
        self,
        symbol: str,
        type: OrderType,
        side: OrderSide,
        amount: float,
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        order = Order(symbol, type, side, amount, price, params)
        self.orders.append(order)

        return order

    async def get_active_orders(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        return self.orders

    async def cancel_order(
        self,
        id: str,
        symbol: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        for order in self.orders:
            if order.get("info", {}).get("orderId") == id:
                self.orders.remove(order)

    async def cancel_all_orders(
        self,
        symbol: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        self.orders = []

    async def get_position(
        self,
        symbol: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Position]:
        if params is None:
            params = {}

        return self.position

    async def get_leverage(
        self,
        symbol: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        if params is None:
            params = {}

        return self._leverage

    async def set_leverage(
        self,
        symbol: str,
        leverage: Union[int, float],
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        self._leverage = leverage

    async def _process_orders(self, current_price: float) -> None:
        for order in self.orders:
            if (order.side == "sell" and order.price > current_price) or (  # type: ignore
                order.side == "buy" and order.price < current_price  # type: ignore
            ):
                if self.position is None:
                    self.position = Position.from_order(order)

                    order_value = order.amount * order.price  # type: ignore

                    if self._available_balance < order_value:
                        logger.warning("CANT OPEN POSITION [NO MONEY]")
                        return None

                    order_fee = 2 * (FEE / 100) * order_value

                    self._fees_paid += order_fee
                    self._available_balance -= order_value + order_fee
                    self.orders.remove(order)

                    if order.side == "sell":
                        self._short_trades += 1
                    elif order.side == "buy":
                        self._long_trades += 1

    async def close_all_positions(self, current_price: float) -> None:
        await self._process_positions(current_price)

    async def _process_positions(self, current_price: float) -> None:
        if self.position is not None:
            if self.position.side == "buy":
                if (
                    current_price < self.position.stop_loss
                    or current_price > self.position.take_profit
                ):
                    profit = self.position.get_profit(current_price)
                    self._available_balance += (
                        profit + current_price * self.position.size
                    )
                    self.position = None

                    if profit > 0:
                        # print("LONG TP", profit)
                        self._long_tp += 1
                    else:
                        # print("LONG SL", profit)
                        self._long_sl += 1

            elif self.position.side == "sell":
                if (
                    current_price > self.position.stop_loss
                    or current_price < self.position.take_profit
                ):
                    profit = self.position.get_profit(current_price)
                    self._available_balance += (
                        profit + current_price * self.position.size
                    )

                    self.position = None
                    if profit > 0:
                        # print("SHORT TP", profit)
                        self._short_tp += 1
                    else:
                        # print("SHORT SL", profit)
                        self._short_sl += 1

    async def get_current_price(self, symbol: str, next_iter: bool = False) -> float:
        current_price = self.data.iloc[self._index]["close"]
        if next_iter:
            self._index += 1
            await self._process_orders(current_price)
            await self._process_positions(current_price)
        return current_price  # type: ignore

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[pd.DataFrame]:
        if params is None:
            params = {}
        if limit and limit > self._index:
            limit = self._index
        return self.data.iloc[self._index - limit : self._index + 1]  # type: ignore

    def result(self) -> Dict[str, float]:
        return {
            "Initial balance": self.initial_balance,
            "Available balance": self._available_balance,
            "Profit": self._available_balance - self.initial_balance,
            "Total trades": self._long_trades + self._short_trades,
            "Long trades": self._long_trades,
            "Long TP": self._long_tp,
            "Long SL": self._long_sl,
            "Short trades": self._short_trades,
            "Short TP": self._short_tp,
            "Short SL": self._short_sl,
            "Fees paid": self._fees_paid,
        }

    @property
    def is_backtester(self) -> bool:
        return True

    async def __aenter__(self) -> BacktestExecutor:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        print(self.result())
        return None


if __name__ == "__main__":
    import asyncio

    async def main() -> None:
        import datetime

        from source.grid_project.src.common.strategy import ExpoGridStrategy
        from source.grid_project.src.common.strategy.expo_grid.grid import Grid
        from source.grid_project.src.common.strategy.expo_grid.settings import (
            ExpoGridStrategySettings,
        )
        from source.grid_project.src.database.core import Database, connection

        strategy_settings = ExpoGridStrategySettings.from_file()
        db = Database(connection)
        historical_data = (
            db.get_historical_data(
                exchange="bybit",
                type_="futures",
                symbol=strategy_settings.symbol,
                timeframe=strategy_settings.timeframe,
                from_=datetime.datetime(2023, 10, 1),
                to=datetime.datetime(2023, 11, 1),
            )
            .drop(columns=["date"])
            .reset_index()
        )
        print(historical_data)
        if historical_data.empty:
            return

        executor = BacktestExecutor(
            data=historical_data, initial_balance=strategy_settings.available_balance
        )
        logger.info(
            f"Connected to {executor.__class__.__name__.replace('Executor', '')}"
        )
        async with executor:
            strategy = ExpoGridStrategy(
                executor=executor, grid=Grid(), settings=strategy_settings
            )
            while executor.is_running:
                await strategy.execute()  # noqa: ERA001, RUF100

    asyncio.run(main())
