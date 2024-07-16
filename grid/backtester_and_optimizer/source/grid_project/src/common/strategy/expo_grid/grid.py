import json
from pathlib import Path
from typing import Dict, Final, List, Tuple

import aiofiles
import numpy as np
from pydantic import BaseModel, ValidationError
from source.grid_project.src.services.data_loader.typedef import Sort
from source.grid_project.src.utils.logger import Logger


RANGE_PERCENT: Final[float] = 0.01  # 0.01 = 1%

logger = Logger(__name__)


class Grid(BaseModel):
    lines: List[float] = []
    values: Dict[float, float] = {}

    @property
    def empty(self) -> bool:
        return not self.lines

    @property
    def middle(self) -> float:
        return (
            self.lines[len(self.lines) // 2] + self.lines[(len(self.lines) // 2) - 1]
        ) / 2

    def is_out_of_range(self, current_price: float) -> bool:
        if self.empty:
            return True
        lower_price, upper_price = self.lines[0], self.lines[-1]
        return (
            lower_price * (1 - RANGE_PERCENT) > current_price
            or upper_price * (1 + RANGE_PERCENT) < current_price
        )

    async def reset(self, save: bool = False) -> None:
        self.lines = []
        self.values = {}
        if save:
            await save_grid(self)

    async def fill_lines(
        self,
        lower_price: float,
        upper_price: float,
        num_of_grids: int,
        available_balance_with_leverage: float,
        save: bool = False,
        disbalance_direction: Sort = "DESCENDING",
    ) -> None:
        if num_of_grids % 2:
            raise ValueError(
                "Number of grids must be an even number. Please provide an even number"
                " of grids for this operation."
            )
        self.lines = list(np.linspace(lower_price, upper_price, num_of_grids))

        values = self._proportional_split(
            available_balance_with_leverage, num_of_grids // 2
        )
        if disbalance_direction == "ASCENDING":
            values = values[::-1]

        self.values = {
            k: v for k, v in zip(self.lines[: num_of_grids // 2][::-1], values)
        } | {k: v for k, v in zip(self.lines[num_of_grids // 2 :], values)}

    @staticmethod
    def _proportional_split(
        total_amount: float,
        num_splits: int,
        decrease_percent: int = 10,
    ) -> List[float]:
        if num_splits <= 0:
            raise ValueError("Number of splits must be greater than 0")

        res: List[float] = []

        for _ in range(num_splits):
            decrease_amount = total_amount * (decrease_percent / 100)
            res.append(decrease_amount)
            total_amount -= decrease_amount

        return res

    def find_closest_grids(self, current_price: float) -> Tuple[float, float]:
        if not isinstance(self.lines, list):
            raise ValueError("Grid is not filled")

        lines = self.lines[1:-1]
        lower_grids = [x for x in lines if x < current_price]
        upper_grids = [x for x in lines if x > current_price]
        if not lower_grids or not upper_grids:
            return 0, 0
        return lower_grids[-1], upper_grids[0]


async def load_grid() -> Grid:
    async with aiofiles.open(Path(__file__).parent / "grid.json", mode="r") as f:
        try:
            grid = Grid(**json.loads(await f.read()))
        except ValidationError as e:
            logger.exception("Error occured during loading grid info", exc_info=e)
            grid = Grid(lines=[], values={})
        return grid


async def save_grid(grid: Grid) -> None:
    async with aiofiles.open(Path(__file__).parent / "grid.json", mode="w") as f:
        await f.write(json.dumps(grid.model_dump(), indent=4))
