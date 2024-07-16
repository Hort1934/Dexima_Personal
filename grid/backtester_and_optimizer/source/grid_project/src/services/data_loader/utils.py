import datetime
from typing import Any, Dict, Optional, TypeAlias, TypedDict, Union

from source.grid_project.src.services.data_loader.typedef import (
    KlineCategory,
    KlineInterval,
    KlineLimit,
)
from source.grid_project.src.utils.converters import convert_timeframe_to_bybit_format
from typing_extensions import Unpack


_Payload: TypeAlias = Dict[str, Union[str, int, Any]]


class RequestParams(TypedDict):
    category: KlineCategory
    symbol: str
    interval: Union[KlineInterval, str]
    start: Optional[Union[int, datetime.datetime]]
    end: Optional[Union[int, datetime.datetime]]
    limit: KlineLimit


def payload_builder(**kwargs: Unpack[RequestParams]) -> _Payload:
    kwargs["interval"] = convert_timeframe_to_bybit_format(kwargs["interval"])

    if kwargs.get("start"):
        kwargs["start"] = int(kwargs["start"].timestamp()) * 1000

    if kwargs.get("end"):
        kwargs["end"] = int(kwargs["end"].timestamp()) * 1000

    return {k: v for k, v in kwargs.items() if v}
