from __future__ import annotations

from enum import Enum
from typing import Final, Optional, Sequence


class Direction(Enum):
    """```
    ^ +y (UP)
    |
    ---> +x (RIGHT)
    ```"""

    UP = (0, 1)
    RIGHT = (1, 0)
    DOWN = (0, -1)
    LEFT = (-1, 0)


directions: Final = (
    Direction.UP,
    Direction.RIGHT,
    Direction.DOWN,
    Direction.LEFT,
)


class FacilityIO:
    def __init__(self, x: int, y: int, direction: Optional[Direction] = None) -> None:
        self.x: Final = x
        self.y: Final = y
        self.direction: Final = direction
        """if missing, this is a non-oriented cell (i.e. just an offset)"""

    def __repr__(self) -> str:
        return (
            (self.x, self.y, self.direction)
            if self.direction is not None
            else (self.x, self.y)
        ).__repr__()

    def translate(self, dx: int, dy: int) -> FacilityIO:
        return FacilityIO(self.x + dx, self.y + dy, self.direction)

    def rotate_cw90(self) -> FacilityIO:
        nd = (
            directions[(directions.index(self.direction) + 1) % 4]
            if self.direction is not None
            else None
        )
        return FacilityIO(-self.y, self.x, nd)


# python polymorphism kinda messy
# class Position(FacilityIO):
#     def __init__(self, x: int, y: int) -> None:
#         super().__init__(x, y, None)


class Facility:
    def __init__(
        self,
        name: str,
        solid: Sequence[FacilityIO],  # supposed to be Position
        input_conveyor: Sequence[FacilityIO] = [],
        input_pipe: Sequence[FacilityIO] = [],
        output_conveyor: Sequence[FacilityIO] = [],
        output_pipe: Sequence[FacilityIO] = [],
    ) -> None:
        self.name: Final = name
        self.solid: Final = solid
        self.input_conveyor: Final = input_conveyor
        self.input_pipe: Final = input_pipe
        self.output_conveyor: Final = output_conveyor
        self.output_pipe: Final = output_pipe

    def __repr__(self) -> str:
        return {
            "name": self.name,
            "solid": self.solid,
            "ic": self.input_conveyor,
            "ip": self.input_pipe,
            "oc": self.output_conveyor,
            "op": self.output_pipe,
        }.__repr__()

    def align(self) -> Facility:
        minx = min(*[p.x for p in self.solid])
        miny = min(*[p.y for p in self.solid])
        return Facility(
            name=self.name,
            solid=[p.translate(-minx, -miny) for p in self.solid],
            input_conveyor=[p.translate(-minx, -miny) for p in self.input_conveyor],
            input_pipe=[p.translate(-minx, -miny) for p in self.input_pipe],
            output_conveyor=[p.translate(-minx, -miny) for p in self.output_conveyor],
            output_pipe=[p.translate(-minx, -miny) for p in self.output_pipe],
        )

    def rotate_cw(self) -> Facility:
        return Facility(
            name=self.name,
            solid=[p.rotate_cw90() for p in self.solid],
            input_conveyor=[p.rotate_cw90() for p in self.input_conveyor],
            input_pipe=[p.rotate_cw90() for p in self.input_pipe],
            output_conveyor=[p.rotate_cw90() for p in self.output_conveyor],
            output_pipe=[p.rotate_cw90() for p in self.output_pipe],
        ).align()
