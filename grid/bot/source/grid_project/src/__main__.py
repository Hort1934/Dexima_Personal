import asyncio

from ccxt.base.errors import ExchangeError

from source.grid_project.src.common.strategy import ExpoGridStrategy
from source.grid_project.src.common.strategy.expo_grid.grid import load_grid
from source.grid_project.src.common.strategy.expo_grid.settings import (
    ExpoGridStrategySettings,
)
from source.grid_project.src.services.executor import BybitExecutor
from source.grid_project.src.utils.logger import Logger


logger = Logger(__name__)


async def main(
    bot_id: int, api_key: str, secret_key: str, params: dict, stop_flag
) -> None:
    expo_instance = ExpoGridStrategySettings(
        symbol=params["symbol"],
        leverage=float(params["leverage"]),
        num_of_grids=int(params["num_of_grids"]),
        available_balance=float(params["available_balance"]),
        timeframe=params["timeframe"],
        price_range=int(params["price_range"]),
        activation_trigger_in_percent=float(params["activation_trigger_in_percent"]),
        distribution_of_grid_lines=params["distribution_of_grid_lines"],
        line_disbalance_direction=params["line_disbalance_direction"],
        short_stop_loss_in_percent=float(params["short_stop_loss_in_percent"]),
        long_stop_loss_in_percent=float(params["long_stop_loss_in_percent"]),
        grid_disbalance_direction=params["grid_disbalance_direction"],
        trend_period_timeframe=params["trend_period_timeframe"],
        trend_period=int(params["trend_period"]),
    )

    executor = BybitExecutor(
        api_key=api_key,
        api_secret=secret_key,
    )
    logger.info(f"Connected to {executor.__class__.__name__.replace('Executor', '')}")
    while not stop_flag.is_set():
        async with executor:
            strategy = ExpoGridStrategy(
                settings=expo_instance,
                executor=executor,
                grid=await load_grid(bot_id=bot_id),
                bot_id=bot_id,
            )

            while True:
                try:
                    logger.info("Checking bybit..")
                    await strategy.execute()
                except ExchangeError as err:
                    logger.exception(
                        "An error occured while executing strategy", exc_info=err
                    )
                await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
