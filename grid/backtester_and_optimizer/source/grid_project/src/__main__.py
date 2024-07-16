import asyncio

from ccxt.base.errors import ExchangeError
from source.grid_project.src.common.strategy import ExpoGridStrategy
from source.grid_project.src.common.strategy.expo_grid.grid import load_grid
from source.grid_project.src.config import settings
from source.grid_project.src.services.executor import BybitExecutor
from source.grid_project.src.utils.logger import Logger


logger = Logger(__name__)


async def main() -> None:
    executor = BybitExecutor(
        api_key=settings.bybit.api_key_testnet,
        api_secret=settings.bybit.api_secret_testnet,
    )
    logger.info(f"Connected to {executor.__class__.__name__.replace('Executor', '')}")
    async with executor:
        strategy = ExpoGridStrategy(executor=executor, grid=await load_grid())
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
