from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from source.grid_project.src.common.executor.base import AbstractExecutor
from source.grid_project.src.common.strategy.base.settings import BaseStrategySettings


S = TypeVar("S", bound="BaseStrategySettings")


class BaseStrategy(ABC, Generic[S]):
    def __init__(
        self,
        executor: AbstractExecutor,
        settings: S,
    ) -> None:
        self.executor = executor
        self.settings = settings

    @abstractmethod
    async def execute(self) -> None:
        raise NotImplementedError("Implement me please!")
