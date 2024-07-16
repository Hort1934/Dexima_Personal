from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from source.grid_project.src.common.executor.base import AbstractExecutor
from source.grid_project.src.common.strategy.base import BaseStrategy
from source.grid_project.src.common.strategy.expo_grid.grid import Grid
from source.grid_project.src.common.strategy.expo_grid.settings import (
    ExpoGridStrategySettings,
)
from source.grid_project.src.common.strategy.expo_grid.trend import Trend
from source.grid_project.src.common.typedef import OrderSide
from source.grid_project.src.utils.logger import Logger


logger = Logger(__name__)


class ExpoGridStrategy(BaseStrategy[ExpoGridStrategySettings]):
    def __init__(
        self,
        executor: AbstractExecutor,
        grid: Grid,
        settings: ExpoGridStrategySettings = ExpoGridStrategySettings.from_file(
            Path(__file__).parent
        ),
    ) -> None:
        super().__init__(executor=executor, settings=settings)
        self.grid = grid

        self._active = False

        if executor.is_backtester:
            logger.disabled = True

    async def set_leverage(self) -> None:
        leverage = await self.executor.get_leverage(self.settings.symbol)
        if leverage != self.settings.leverage:
            logger.info("Current position leverage doesn't match strategy's leverage.")
            await self.executor.set_leverage(
                self.settings.symbol, self.settings.leverage
            )
            logger.info(
                f"Position leverage has been changed from {leverage} to"
                f" {self.settings.leverage}"
            )

    async def execute(self) -> None:
        await self.set_leverage()

        current_price = await self.executor.get_current_price(
            self.settings.symbol, True
        )
        position = await self.executor.get_position(self.settings.symbol)
        logger.info(f"Active position: {position}")
        active_orders = await self.executor.get_active_orders(self.settings.symbol)
        for order in active_orders:
            logger.info(f"Active order: {order}")
        if not self.grid.empty and self.grid.is_out_of_range(current_price):
            await self._process_out_of_range(current_price, active_orders, position)
            self._active = False
            logger.info(
                "Grid is out of market! Cancelling orders, closing position and"
                " reseting grid lines.."
            )
        if self.grid.empty:
            lower, upper = await self._get_lower_and_upper()
            await self.grid.fill_lines(
                lower_price=lower,
                upper_price=upper,
                num_of_grids=self.settings.num_of_grids,
                available_balance_with_leverage=self.settings.available_balance
                * self.settings.leverage,
                save=not self.executor.is_backtester,
                disbalance_direction=self.settings.line_disbalance_direction,
            )
            logger.info("Grid has been updated with new grid lines.")

        if not self._active:
            _checklist = [self.grid.middle, current_price]
            self._active = max(_checklist) / min(_checklist) <= 1.01
            logger.info(
                f"Middle price: {self.grid.middle}. Current price: {current_price}."
                f" Triggered: {self._active}"
            )

        if self._active and not position and not active_orders:
            await self._process_no_positions()

        if position and active_orders:
            for order in active_orders:
                order_id = order.get("info", {}).get("orderId")
                if order_id:
                    await self.executor.cancel_order(
                        id=order_id,
                        symbol=self.settings.symbol,
                    )
                    logger.info(
                        f"Order {order_id} has been cancelled due to active position."
                    )

    async def _process_out_of_range(
        self,
        current_price: float,
        active_orders: Optional[Dict[str, Any]] = None,
        position: Optional[Dict[str, Any]] = None,
    ) -> None:
        if active_orders:
            await self.executor.cancel_all_orders(self.settings.symbol)

        if position:
            side: OrderSide = (
                "buy" if position.get("info", {}).get("side") == "Sell" else "sell"
            )
            amount = float(position.get("info", {}).get("size"))
            if not self.executor.is_backtester:
                await self.executor.create_order(
                    symbol=self.settings.symbol,
                    type="market",
                    side=side,
                    amount=amount,
                )
            else:
                self.executor.close_all_position(current_price)  # type: ignore[attr-defined]
            logger.info("Position closed using market price.")
        await self.grid.reset(save=not self.executor.is_backtester)

    async def _process_no_positions(self) -> None:
        current_price = await self.executor.get_current_price(self.settings.symbol)
        trend = await self._determine_trend()
        side: OrderSide = "sell" if trend == Trend.BEARISH else "buy"
        lower_grid, upper_grid = self.grid.find_closest_grids(current_price)

        if not lower_grid or not upper_grid:
            return None

        lower_tp, lower_sl = self._get_tp_sl(lower_grid, side)
        upper_tp, upper_sl = self._get_tp_sl(upper_grid, side)

        await self.executor.create_order(
            symbol=self.settings.symbol,
            type="limit",
            side=side,
            amount=self.grid.values[lower_grid] / lower_grid,
            price=lower_grid,
            params={
                "takeProfit": lower_tp,
                "stopLoss": lower_sl,
                "triggerPrice": lower_grid,
                "triggerDirection": 2,
            },
        )
        await self.executor.create_order(
            symbol=self.settings.symbol,
            type="limit",
            side=side,
            amount=self.grid.values[upper_grid] / upper_grid,
            price=upper_grid,
            params={
                "takeProfit": upper_tp,
                "stopLoss": upper_sl,
                "triggerPrice": upper_grid,
                "triggerDirection": 1,
            },
        )

        logger.info(f"Placed 2 orders on {lower_grid} and {upper_grid} levels")

    async def _determine_trend(self) -> Trend:
        historical_data = await self.executor.fetch_ohlcv(
            symbol=self.settings.symbol,
            timeframe=self.settings.timeframe,
            limit=self.settings.trend_period,
        )

        if historical_data is None:
            raise ValueError("Error while fetching historical data to determine trend")
        historical_data.index = pd.RangeIndex(0, historical_data.shape[0])
        if (
            historical_data.shape[0] >= self.settings.trend_period
            and historical_data["open"][0]
            < historical_data["close"][historical_data.shape[0] - 1]
        ):
            return Trend.BULLISH
        return Trend.BEARISH

    async def _get_lower_and_upper(self) -> Tuple[float, float]:
        historical_data = await self.executor.fetch_ohlcv(
            symbol=self.settings.symbol,
            timeframe=self.settings.timeframe,
            limit=self.settings.price_range,
        )

        if historical_data is None:
            raise ValueError(
                "Error while fetching historical data to get lower and upper lines"
            )

        return historical_data["low"].min(), historical_data["high"].max()

    def _get_tp_sl(
        self,
        entry_price: float,
        side: OrderSide,
    ) -> Tuple[float, float]:
        lower, upper = self.grid.find_closest_grids(entry_price)
        sl_in_percent = (
            self.settings.long_stop_loss_in_percent
            if side == "buy"
            else self.settings.short_stop_loss_in_percent
        )

        match side:
            case "buy":
                return (
                    upper,
                    max(entry_price - entry_price * (sl_in_percent / 100), lower),
                )
            case "sell":
                return (
                    lower,
                    min(entry_price + entry_price * (sl_in_percent / 100), upper),
                )
