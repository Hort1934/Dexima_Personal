from http import HTTPStatus
from typing import (
    Any,
    Dict,
    Generic,
    Optional,
    TypeVar,
    Union,
)

from pydantic import BaseModel


ResultType = TypeVar("ResultType", bound=Any)


class Response(BaseModel, Generic[ResultType]):
    status_code: Union[HTTPStatus, int]
    url: Optional[str] = None
    result: Optional[ResultType] = None
    headers: Optional[Dict[str, Any]] = None
    cookies: Optional[Dict[str, Any]] = None
