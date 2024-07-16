from typing import Any, Literal, Type, TypeAlias, Union

from ccxt.async_support.base.exchange import Exchange


OrderSide: TypeAlias = Literal["buy", "sell"]
OrderType: TypeAlias = Literal["market", "limit"]

TradeType: TypeAlias = Literal["long", "short", "buy", "sell"]

ConnectorType: TypeAlias = Union[Type[Exchange], Type[Any]]
