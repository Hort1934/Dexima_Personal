from __future__ import annotations

import uuid
from types import TracebackType
from typing import Any, ClassVar, Dict, List, Optional, Type, Union

import pandas as pd
from source.grid_project.src.common.exceptions import CCXTAPIError
from source.grid_project.src.common.executor.base import AbstractExecutorWithConnector
from source.grid_project.src.common.typedef import ConnectorType, OrderSide, OrderType
from source.grid_project.src.utils.logger import Logger


logger = Logger(__name__)


class CCXTCryptoExecutor(AbstractExecutorWithConnector):
    _default_params: ClassVar[Dict[str, str]] = {"subType": "linear"}

    def __init__(
        self,
        connector: ConnectorType,
        api_key: str,
        api_secret: str,
    ) -> None:
        super().__init__(connector=connector)
        self.api_key = api_key
        self.api_secret = api_secret

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

        return await self.connector.create_order(
            symbol=symbol,
            type=type,
            side=side,
            amount=amount,
            price=price,
            params=(params | self._default_params | {"clientOrderId": uuid.uuid4()}),
        )

    async def get_active_orders(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        return [
            order
            for order in await self.connector.fetch_open_orders(
                symbol=symbol,
                since=since,
                limit=limit,
                params=(params | self._default_params),
            )
            if order.get("info", {}).get("orderLinkId")
        ]

    async def cancel_order(
        self,
        id: str,
        symbol: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        return await self.connector.cancel_order(
            id=id,
            symbol=symbol,
            params=(params | self._default_params),
        )

    async def cancel_all_orders(
        self,
        symbol: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        return await self.connector.cancel_all_orders(
            symbol=symbol,
            params=(params | self._default_params),
        )

    async def get_position(
        self,
        symbol: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        if params is None:
            params = {}

        position: Dict[str, Any] = await self.connector.fetch_position(symbol, params)
        if position.get("info", {}).get("avgPrice", "0") != "0":
            return position
        return None

    async def get_leverage(
        self,
        symbol: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> Optional[float]:
        if params is None:
            params = {}

        position = await self.connector.fetch_position(
            symbol=symbol,
            params=(params | self._default_params),
        )
        if position:
            return float(position.get("info", {}).get("leverage", "0"))
        return None

    async def set_leverage(
        self,
        symbol: str,
        leverage: Union[int, float],
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        return await self.connector.set_leverage(
            symbol=symbol,
            leverage=leverage,
            params=(params | self._default_params),
        )

    async def get_current_price(self, symbol: str, next_iter: bool = False) -> float:
        ticker_info: Dict[str, str] = await self.connector.fetch_ticker(symbol)
        current_price: Optional[str] = ticker_info.get("last")
        if current_price is None:
            exchange_name = self.__class__.__name__.replace("Executor", "")
            raise CCXTAPIError(
                f"{exchange_name} returned None. No data or result was found."
            )
        return float(current_price)

    async def _connect(self) -> None:
        self.connector = self.connector(
            {
                "apiKey": self.api_key,
                "secret": self.api_secret,
            }
        )
        self.connector.set_sandbox_mode(True)  # test one
        # self.connector.set_sandbox_mode(False)  # prod one  # noqa: ERA001, W505

    async def _disconnect(self) -> None:
        await self.connector.close()

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

        raw_data = await self.connector.fetch_ohlcv(
            symbol,
            timeframe,
            since,
            limit,
            (params | self._default_params),
        )
        return await self._to_df(raw_data)

    @staticmethod
    async def _to_df(data: List[List[Union[int, float]]]) -> Optional[pd.DataFrame]:
        df: Optional[pd.DataFrame] = None
        try:
            df = pd.DataFrame(
                data=data,
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
            )
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
        except ValueError as e:
            logger.exception(
                "Error while converting historical data to df",
                exc_info=e,
            )
        finally:
            return df

    async def __aenter__(self) -> CCXTCryptoExecutor:
        await self._connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self._disconnect()
