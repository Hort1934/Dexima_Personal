from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union

from source.grid_project.src.common.typedef import ConnectorType, OrderSide, OrderType


class AbstractExecutor(ABC):
    @abstractmethod
    def create_order(
        self,
        symbol: str,
        type: OrderType,
        side: OrderSide,
        amount: float,
        price: Optional[float] = None,
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def get_active_orders(
        self,
        symbol: Optional[str] = None,
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def cancel_order(
        self,
        id: str,
        symbol: Optional[str] = None,
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def cancel_all_orders(
        self,
        symbol: Optional[str] = None,
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def get_current_price(self, symbol: str, next_iter: bool = False) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def get_position(
        self,
        symbol: str,
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def get_leverage(
        self,
        symbol: str,
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def set_leverage(
        self,
        symbol: str,
        leverage: Union[int, float],
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: Dict[str, Any] = {},
    ) -> Any:
        raise NotImplementedError("Implement me please!")

    @property
    def is_backtester(self) -> bool:
        return False


class AbstractExecutorWithConnector(AbstractExecutor):
    def __init__(self, connector: ConnectorType) -> None:
        self.connector = connector
