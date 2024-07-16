import json
from abc import ABC
from pathlib import Path
from typing import Any, Dict, List, Type, TypeVar

from pydantic import BaseModel


Self = TypeVar("Self", bound="BaseStrategySettings")


class BaseStrategySettings(ABC, BaseModel):
    optimization: Dict[str, List[Any]]

    @classmethod
    def from_file(cls: Type[Self], cwd: Path) -> Self:
        with Path.open(cwd / "settings.json", mode="r", encoding="utf-8") as f:
            return cls(**json.load(f))
