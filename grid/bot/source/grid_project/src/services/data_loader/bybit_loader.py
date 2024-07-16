from __future__ import annotations

import datetime
from types import TracebackType
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

import pandas as pd

from source.grid_project.src.services.data_loader.typedef import (
    KlineCategory,
    KlineInterval,
    KlineLimit,
)
from source.grid_project.src.services.data_loader.utils import payload_builder
from source.grid_project.src.services.session.aiohttp import AiohttpSession
from source.grid_project.src.services.session.base import BaseSession
from source.grid_project.src.utils.logger import Logger


logger = Logger(__name__)


def _to_df(data: List[List[Union[int, float]]]) -> pd.DataFrame:
    df = pd.DataFrame(
        data=data,
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "turnover",
        ],
    )
    df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
    df[["open", "high", "low", "close", "volume", "turnover"]] = df[
        ["open", "high", "low", "close", "volume", "turnover"]
    ].astype(float)
    return df


class BybitDataLoader:
    mainnet_api: str = "https://api.bybit.com/"
    testnet_api: str = "https://api-testnet.bybit.com"

    def __init__(self, session: Optional[BaseSession] = None) -> None:
        self._session = session or AiohttpSession(api=self.mainnet_api)

    async def get_historical_data(
        self,
        category: KlineCategory,
        symbol: str,
        interval: KlineInterval,
        start: Optional[datetime.datetime] = None,
        end: Optional[datetime.datetime] = None,
        limit: KlineLimit = 200,
    ) -> pd.DataFrame:
        payload = payload_builder(
            category=category,
            symbol=symbol,
            interval=interval,
            start=start,
            end=end,
            limit=limit,
        )
        endpoint = f"v5/market/kline?{'&'.join(f'{k}={v}' for k, v in payload.items())}"
        response: Dict[str, Any] = await self._session(method="GET", endpoint=endpoint)

        return _to_df(response["result"].get("list", []))

    async def __aenter__(self) -> BybitDataLoader:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        await self._session.close()
