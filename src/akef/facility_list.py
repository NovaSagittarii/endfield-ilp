from pathlib import Path
from typing import Final, MutableSequence, Tuple

import yaml

from akef.facility import Facility, FacilityIO, directions

MODIFIER_FLAGS: Final = "iocps"
"""
i - input\\
o - output\\
c - conveyor (solids)\\
p - pipe (liquids)\\
s - shift (forwards for input, backwards for output)\\
"""


def parse_facility(grid: list[str]) -> Facility:
    n = len(grid)
    # m = len(grid[0])
    solid: MutableSequence[FacilityIO] = []
    io_cells: MutableSequence[Tuple[FacilityIO, str]] = []
    for i, row in enumerate(grid):
        for j, c in enumerate(row):
            if c == "#":
                solid.append(FacilityIO(x=j, y=i))
            elif c in "^>v<":
                # pick a direction and walk in that direction to accumulate
                # modifier flags that pertain to a facility I/O port
                dir = directions["^>v<".index(c)]
                for d in directions:
                    di, dj = d.value
                    ni, nj = i + di, j + dj
                    if 0 <= ni < n and 0 <= nj < len(grid[ni]):
                        if grid[ni][nj] in MODIFIER_FLAGS:
                            w = 1
                            flags = ""
                            while True:
                                ni, nj = i + di * w, j + dj * w
                                if 0 <= ni < n and 0 <= nj < len(grid[ni]):
                                    flags += grid[ni][nj]
                                    w += 1
                                else:
                                    break
                            # print(f"{k}[{i}][{j}] {c} :: {dir} :: {flags}")
                            fio = FacilityIO(x=j, y=i, direction=dir)
                            io_cells.append((fio, flags))
                            break
                else:
                    raise ValueError(
                        f"Missing flags for {c} on line {i} char {j} of {k}"
                    )

    return Facility(
        k,
        solid=solid,
        input_conveyor=[c for c, f in io_cells if "i" in f and "c" in f],
        input_pipe=[c for c, f in io_cells if "i" in f and "p" in f],
        output_conveyor=[c for c, f in io_cells if "o" in f and "c" in f],
        output_pipe=[c for c, f in io_cells if "o" in f and "p" in f],
    ).align()


_facility_list: MutableSequence[Facility] = []
with open(Path(__file__).resolve().parent / "facility_list.yaml", "r") as file:
    _data: Final[dict] = yaml.safe_load(file.read())
    for k, v in _data.items():
        layouts: MutableSequence[Facility] = []
        grid: list[str] = v["layout"].strip().split("\n")
        layouts.append(parse_facility(grid))

        if "layout2" in v:
            layouts.append(parse_facility(v["layout2"].strip().split("\n")))

        # NOTE: other properties (power_range, special, etc) are currently not used
        _facility_list.extend(layouts)

facility_list: Final = tuple(_facility_list)

if __name__ == "__main__":
    for f in facility_list:
        print(f)
