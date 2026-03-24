from __future__ import annotations

from enum import Enum
from functools import cache
from typing import (
    Final,
    MutableSequence,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    TypeAlias,
)

XYTuple: TypeAlias = Tuple[int, int]


class Direction(Enum):
    """```
    ^ +y (UP)
    |
    ---> +x (RIGHT)
    ```"""

    UP = (0, -1)
    RIGHT = (1, 0)
    DOWN = (0, 1)
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

    def as_xy(self) -> XYTuple:
        """
        Discards direction and returns an XYTuple.
        """

        return (self.x, self.y)

    def unravel(self, N: int, M: int) -> Tuple[int, int]:
        """
        Suppose (x, y) are on a (N, M) sized grid. Return the unravel_index of
        (x, y) on this grid and direction index (for usage as a LP variable)

        Returns (c, d)
        """
        if 0 <= self.x < N and 0 <= self.y < M:
            return self.x + self.y * N, directions.index(self.direction)
        else:
            raise IndexError()


# python polymorphism kinda messy
# class Position(FacilityIO):
#     def __init__(self, x: int, y: int) -> None:
#         super().__init__(x, y, None)


class FacilityProperties(NamedTuple):
    special: bool = False
    requires_power: bool = True
    power_range: int = 0


class Facility:
    """
    The layout of a facility -- how a facility affects the cells around it,
    such as by occupying it, powering it, input/output ports, etc.
    """

    def __init__(
        self,
        name: str,
        solid: Sequence[FacilityIO],  # supposed to be Position
        input_conveyor: Sequence[FacilityIO] = [],
        input_pipe: Sequence[FacilityIO] = [],
        output_conveyor: Sequence[FacilityIO] = [],
        output_pipe: Sequence[FacilityIO] = [],
        props: FacilityProperties = FacilityProperties(),
    ) -> None:
        self.name: Final = name
        self.solid: Final = solid
        self.input_conveyor: Final = input_conveyor
        self.input_pipe: Final = input_pipe
        self.output_conveyor: Final = output_conveyor
        self.output_pipe: Final = output_pipe
        self.props = props

        minx = min(*[p.x for p in self.solid])
        miny = min(*[p.y for p in self.solid])
        maxx = max(*[p.x for p in self.solid])
        maxy = max(*[p.y for p in self.solid])
        self.width: Final = maxx - minx + 1
        self.height: Final = maxy - miny + 1

    def __repr__(self) -> str:
        return {
            "name": self.name,
            "props": self.props,
            "solid": self.solid,
            "ic": self.input_conveyor,
            "ip": self.input_pipe,
            "oc": self.output_conveyor,
            "op": self.output_pipe,
        }.__repr__()

    def align(self) -> Facility:
        """
        Translate the cells such that (0, 0) is the left-top occupied cell.
        Returns a copy.
        """
        minx = min(*[p.x for p in self.solid])
        miny = min(*[p.y for p in self.solid])
        return Facility(
            name=self.name,
            solid=[p.translate(-minx, -miny) for p in self.solid],
            input_conveyor=[p.translate(-minx, -miny) for p in self.input_conveyor],
            input_pipe=[p.translate(-minx, -miny) for p in self.input_pipe],
            output_conveyor=[p.translate(-minx, -miny) for p in self.output_conveyor],
            output_pipe=[p.translate(-minx, -miny) for p in self.output_pipe],
            props=self.props,
        )

    def rotate_cw(self) -> Facility:
        """
        Rotates all offsets by 90 degrees clockwise, then aligns.
        Returns a copy.
        """
        return Facility(
            name=self.name,
            solid=[p.rotate_cw90() for p in self.solid],
            input_conveyor=[p.rotate_cw90() for p in self.input_conveyor],
            input_pipe=[p.rotate_cw90() for p in self.input_pipe],
            output_conveyor=[p.rotate_cw90() for p in self.output_conveyor],
            output_pipe=[p.rotate_cw90() for p in self.output_pipe],
            props=self.props,
        ).align()


class ActiveFacility:
    """
    Specialized instance of a facility that has a fixed recipe.
    The input port items and output port items are **known**.
    """

    def __init__(
        self,
        facility: Facility,
        input: dict[str, int],
        output: dict[str, int],
    ) -> None:
        self.facility: Final = facility
        self.input: Final = input
        self.output: Final = output

    def rotate_cw(self, amt: int = 1) -> ActiveFacility:
        assert 0 <= amt <= 3, "Range of rotations"
        f = self.facility
        for _ in range(amt):
            f = f.rotate_cw()
        return ActiveFacility(
            facility=f,
            input=self.input,
            output=self.output,
        )

    def occupied_region(self, anchor: XYTuple) -> Sequence[XYTuple]:
        return [p.translate(*anchor).as_xy() for p in self.facility.solid]

    @cache
    def powered_region(self, anchor: XYTuple) -> Sequence[XYTuple]:
        # maybe generalize later... though relay is strictly worse
        if self.facility.name == "pylon":
            N = 2
            R = 5
            cells: MutableSequence[FacilityIO] = []
            for x in range(-R, N + R):
                for y in range(-R, N + R):
                    if x < 0 or x >= N or y < 0 or y >= N:
                        cells.append(FacilityIO(x=x, y=y))
            return [p.translate(*anchor).as_xy() for p in cells]
        return []

    def input_ports(self, anchor: XYTuple) -> Sequence[FacilityIO]:
        return [p.translate(*anchor) for p in self.facility.input_conveyor]

    def output_ports(self, anchor: XYTuple) -> Sequence[FacilityIO]:
        return [p.translate(*anchor) for p in self.facility.output_conveyor]
