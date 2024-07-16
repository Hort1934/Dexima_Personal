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
        if len(self.lines) % 2 == 1:
            return self.lines[len(self.lines) // 2]
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

    async def reset(self, bot_id: int, save: bool = False) -> None:
        self.lines = []
        self.values = {}
        if save:
            await save_grid(self, bot_id=bot_id)

    async def fill_lines(
        self,
        lower_price: float,
        upper_price: float,
        num_of_grids: int,
        available_balance_with_leverage: float,
        save: bool = False,
        disbalance_direction: Sort = "DESCENDING",
    ) -> None:
        self.lines = list(np.linspace(lower_price, upper_price, num_of_grids))

        values = self._proportional_split(
            available_balance_with_leverage,
            num_of_grids // 2 if num_of_grids % 2 == 0 else num_of_grids // 2 + 1,
        )
        if disbalance_direction == "ASCENDING":
            values = values[::-1]

        self.values = {
            k: v
            for k, v in zip(
                self.lines[
                    : (
                        num_of_grids // 2
                        if num_of_grids % 2 == 0
                        else num_of_grids // 2 + 1
                    )
                ][::-1],
                values,
            )
        } | {
            k: v
            for k, v in zip(
                self.lines[
                    (
                        num_of_grids // 2
                        if num_of_grids % 2 == 0
                        else num_of_grids // 2 + 1
                    ) :
                ],
                values,
            )
        }

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
            if not lower_grids:
                return self.lines[0], upper_grids[0]
            return lower_grids[-1], self.lines[-1]
        return lower_grids[-1], upper_grids[0]


async def load_grid(bot_id: int) -> Grid:
    context = {"lines": [], "values": {}}

    # Specify the file path
    file_path = f"{bot_id}.json"

    # Write the context to the JSON file
    with open(Path(__file__).parent / file_path, "w") as json_file:
        json.dump(context, json_file, indent=4)

    async with aiofiles.open(Path(__file__).parent / f"{bot_id}.json", mode="r") as f:
        try:
            grid = Grid(**json.loads(await f.read()))
        except ValidationError as e:
            logger.exception("Error occured during loading grid info", exc_info=e)
            grid = Grid(lines=[], values={})
        return grid


async def save_grid(grid: Grid, bot_id: int) -> None:
    async with aiofiles.open(Path(__file__).parent / f"{bot_id}.json", mode="w") as f:
        await f.write(json.dumps(grid.model_dump(), indent=4))
