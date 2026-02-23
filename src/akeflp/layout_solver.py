"""
Docstring for akeflp.layout_solver
"""

from __future__ import annotations

from itertools import chain
from typing import Final, MutableSequence, Tuple, TypeAlias

import numpy as np
from scipy.optimize import linprog  # type: ignore

from akef.facility import ActiveFacility
from akef.facility_list import directions, facility_dict, facility_list
from akef.items import items
from akef.resource import raw_resources

# from scipy.sparse import dok_array, sparray


AT: TypeAlias = np.ndarray  # | sparray


def solve(shape: Tuple[int, int], into_depot: dict[str, int]) -> None:
    N, M = shape

    # set is faster but for list is small enough it's not that bad, nice cuz concise
    _items: list[str] = []
    _facility_list: list[ActiveFacility] = []

    def dfs(u: str) -> None:
        if u not in _items:
            recipe = items[u]
            ok = False
            for facility in facility_list:
                if facility.name == recipe.action or (
                    facility.name == "depot_unloader" and recipe.name in raw_resources
                ):
                    if recipe.name in _items:
                        break
                    _items.append(recipe.name)
                    _facility_list.append(
                        ActiveFacility(
                            facility=facility,
                            input={k.name: v for v, k in recipe.inputs},
                            output={recipe.name: recipe.output},
                        )
                    )
                    for _, k in recipe.inputs:
                        dfs(k.name)
                    ok = True
            assert ok, f"Cannot produce {recipe.name} with any facility."

    for item_name in into_depot.keys():
        _facility_list.append(
            ActiveFacility(
                facility=facility_dict["protocol_stash"],
                input={item_name: 1},
                output={},
            )
        )
        dfs(item_name)

    print(f"on {N}x{M} grid. produce", into_depot)
    print(_items)
    print(
        "\n".join(
            [
                {
                    "facility": f.facility.name,
                    "input": f.input,
                    "output": f.output,
                }.__repr__()
                for f in _facility_list
            ]
        )
    )

    # generate all rotation variants
    _facility_list = list(
        chain(*[[f.rotate_cw(i) for i in range(4)] for f in _facility_list])
    )
    _facility_list.append(ActiveFacility(facility_dict["pylon"], {}, {}))

    Ict: Final = len(_items)
    Fct: Final = len(_facility_list)

    C: Final = range(0, N * M)
    Cxy: Final = tuple((x + y * N, x, y) for x in range(N) for y in range(M))
    D: Final = range(4)
    Dp: Final = [[0, 2], [1, 3]]
    I: Final = range(Ict)
    # F: Final = range(Fct)
    F_enum = [*enumerate(_facility_list)]
    F_powered: Final = [*filter(lambda x: x[1].facility.props.requires_power, F_enum)]
    F_power_src: Final = [*filter(lambda x: x[1].facility.props.power_range, F_enum)]
    Xcdi = np.arange(N * M * 4 * Ict).reshape((N * M, 4, Ict))
    Xfc = (np.arange(N * M * Fct) + Xcdi.size).reshape((Fct, N * M))
    Xend = Xcdi.size + Xfc.size

    A_ub: MutableSequence[AT] = []
    b_ub: MutableSequence[int] = []
    constraint_desc: MutableSequence[str] = []  # for debug

    class ConstraintRow:
        def __init__(
            self,
            A_ub: MutableSequence[AT],
            b_ub: MutableSequence[int],
            *,
            b: int = 0,
            msg: str = "",
        ) -> None:
            self.A_ub: Final = A_ub
            self.b_ub: Final = b_ub
            self.row: Final = np.zeros((Xend,), dtype=np.int8)
            # dok_array((Xend,), dtype=np.int8)
            # np.zeros((Xend,), dtype=np.int8)
            # np.ndarray[tuple[int], np.dtype[np.int8]]

            self.b: int = b
            constraint_desc.append(msg)

        def set_b(self, b: int) -> None:
            """set the upper bound"""
            self.b = b

        def __enter__(self) -> ConstraintRow:
            return self

        def __exit__(self, *args: object) -> None:
            self.A_ub.append(self.row)
            # self.A_ub.append(self.row.tocsr())
            self.b_ub.append(self.b)

    # MARK: Constraints
    # (1) - Conveyors are single item.
    for c in C:
        for d in D:
            with ConstraintRow(A_ub, b_ub, b=1, msg="1") as w:
                for i in I:
                    w.row[Xcdi[c][d][i]] = 1

    # (2)
    for c in C:
        with ConstraintRow(A_ub, b_ub, b=2, msg="2") as w:
            for d in D:
                for i in I:
                    w.row[Xcdi[c][d][i]] = 1

    # (3)
    for c in C:
        for dp in Dp:
            with ConstraintRow(A_ub, b_ub, b=1, msg="3") as w:
                for d in dp:
                    for i in I:
                        w.row[Xcdi[c][d][i]] = 1

    # (4) - Conveyors have a source of items. Conservation of items.
    for c, x, y in Cxy:
        for i, item in enumerate(_items):
            with ConstraintRow(A_ub, b_ub, b=0, msg=f"4 {c} {d} {i}") as w:
                for d in D:
                    w.row[Xcdi[c][d][i]] = 1
                    for d2, nd in enumerate(directions):  # candidate inflow
                        if (d - d2) % 4 == 2:
                            continue
                        dx, dy = nd.value
                        px, py = x - dx, y - dy
                        if 0 <= px < N and 0 <= py < M:
                            c2 = px + py * N
                            w.row[Xcdi[c2][d2][i]] = -1
                    for f, af in enumerate(_facility_list):
                        if not af.output.get(item):
                            continue
                        for c2, x2, y2 in Cxy:
                            for pos in af.output_ports((x2, y2)):
                                try:
                                    c3, d2 = pos.unravel(N, M)
                                    # if c == c3 and d == d2:
                                    #     w.row[Xfc[f][c2]] = -1
                                    if c == c3 and (d - d2) % 4 != 2:
                                        w.row[Xfc[f][c2]] = -1
                                except IndexError:
                                    pass

    # (5) - Facility does not overlap with other facility or conveyor belt.
    for c, x, y in Cxy:
        with ConstraintRow(A_ub, b_ub, b=4, msg=f"5:{c} {x} {y}") as w:
            for f, af in enumerate(_facility_list):
                for c2, x2, y2 in Cxy:
                    if (x, y) in af.occupied_region((x2, y2)):
                        w.row[Xfc[f][c2]] = 4
            for d in D:
                for i in I:
                    w.row[Xcdi[c][d][i]] = 1

    # (6) - Facility is powered
    for c, x, y in Cxy:
        for f, af in F_powered:
            with ConstraintRow(
                A_ub, b_ub, b=0, msg=f"6:{c} {x} {y} {af.facility.name}"
            ) as w:
                w.row[Xfc[f][c]] = 1
                for f2, af2 in F_power_src:
                    # TODO: this part is VERY SLOW :sob:
                    for x2, y2 in af.occupied_region((x, y)):
                        for c3, x3, y3 in Cxy:
                            if (x2, y2) in af2.powered_region((x3, y3)):
                                w.row[Xfc[f2][c3]] = -1

    # (7) - Facility input satisfied
    for c, x, y in Cxy:
        for i, item in enumerate(_items):
            for f, af in enumerate(_facility_list):
                with ConstraintRow(
                    A_ub,
                    b_ub,
                    b=0,
                    msg=f"7:[{f} {c} {i}] {x},{y} {item} {af.facility.name}",
                ) as w:
                    w.row[Xfc[f][c]] = af.input.get(item, 0)
                    for pos in af.input_ports((x, y)):
                        assert pos.direction is not None, "expect oriented FIO"
                        try:
                            c2, d = pos.unravel(N, M)
                            w.row[Xcdi[c2][d][i]] = -1
                        except IndexError:
                            pass  # just ignore it (no way to fit this input port)

    # (8) - Facility output not exceeded
    big = 127 - 3
    for f, af in enumerate(_facility_list):
        for c, x, y in Cxy:
            for i, item in enumerate(_items):
                with ConstraintRow(
                    A_ub,
                    b_ub,
                    b=big + af.output.get(item, 0),
                    msg=f"8:[{f} {c} {i}] {x},{y} {item} {af.facility.name}",
                ) as w:
                    w.row[Xfc[f][c]] = big
                    for pos in af.output_ports((x, y)):
                        try:
                            c2, d = pos.unravel(N, M)
                            for d2 in D:
                                if (d - d2) % 4 != 2:
                                    w.row[Xcdi[c2][d2][i]] = 1
                        except IndexError:
                            pass

    # (9) - Layout requirements, how much needs to go into depot.
    for k, v in into_depot.items():
        with ConstraintRow(A_ub, b_ub, b=-v) as w:
            for c in C:
                for f, af in enumerate(_facility_list):
                    if af.facility.name == "protocol_stash" and af.input.get(k):
                        w.row[Xfc[f][c]] = -1

    bounds = [(0, 0) for _ in range(Xend)]
    # disallow facilities to go outside the layout grid
    for c, x, y in Cxy:
        for f, af in enumerate(_facility_list):
            if af.facility.width + x > N or af.facility.height + y > M:
                bounds[Xfc[f][c]] = (0, 0)
            # restrict allowed position of depot_unloader
            # from akef.facility import Direction
            # from typing import cast
            # if af.facility.name == "depot_unloader" and (
            #     x > 0
            #     or cast(Direction, af.facility.output_conveyor[0].direction).name
            #     != "RIGHT"
            # ):
            #     bounds[Xfc[f][c]] = (0, 0)

    # MARK: Solve
    print("A_ub size=", Xend * len(A_ub))
    print(f"{Xend} variables, {len(A_ub)} constraints", flush=True)
    res = linprog(
        [0 for _ in range(Xend)],  # hopefully it terminates faster?
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=bounds,
        integrality=1,
        # options={"presolve": False},
    )
    print(res)

    # def cxy(x: int, y: int) -> int:
    #     return x + y * N
    # res.x = [0 for _ in range(Xend)]
    # def place_facility(x: int, y: int, fname: str, dir: str) -> None:
    #     for f, af in enumerate(_facility_list):
    #         if af.facility.name == fname and (
    #             not af.facility.input_conveyor
    #             or af.facility.input_conveyor[0].direction.name == dir
    #         ):
    #             res.x[Xfc[f][cxy(x, y)]] = 1
    #             break
    #     else:
    #         raise ValueError(f"Can't find facility <{fname}> with dir <{dir}>")
    # def place_belt(x: int, y: int, item: str, path: str) -> None:
    #     i = _items.index(item)
    #     for dc in path:
    #         d = "^>v<".index(dc)
    #         dx, dy = directions[d].value
    #         res.x[Xcdi[cxy(x, y)][d][i]] = 1
    #         x += dx
    #         y += dy
    # place_facility(1, 1, "seed", "DOWN")
    # place_facility(7, 1, "plant", "DOWN")
    # place_facility(1, 7, "plant", "DOWN")
    # place_facility(7, 7, "protocol_stash", "DOWN")
    # place_facility(7, 10, "pylon", "")
    # place_belt(2, 6, "buckflower_seed", "v")
    # place_belt(1, 12, "buckflower", "<^^^^^^^^^^^^>v")
    # place_belt(5, 6, "buckflower_seed", ">^^^^^^>v")
    # place_belt(9, 6, "buckflower", "v")

    # MARK: Reconstruct
    assert res.x is not None, "Expect possible."
    if res.x is None:
        return
    res.x = tuple(map(round, res.x))  # round +eps to 0

    for i, Ab in enumerate(zip(A_ub, b_ub)):
        A, b = Ab
        if A @ res.x > b:
            print(f"Constraint violated: idx={i} msg={constraint_desc[i]}")
            row = A
            print(row @ res.x, "<=? 0")
            print(dict(sorted({i: int(x) for i, x in enumerate(row) if x}.items())))
            break
        # assert A @ res.x <= b, f"{A} {res.x} = {A @ res.x} </= {b}"
    else:
        print("Solution is valid. Constraints passed.")
    print("sol:", set(i for i, x in enumerate(res.x) if x))

    layout = [["░" for _ in range(N)] for _ in range(M)]
    for c, x, y in Cxy:
        for f, af in enumerate(_facility_list):
            if res.x[Xfc[f][c]]:
                print("-", af.facility.name, "@", (x, y), [f, c])
                # for pos in af.input_ports((x, y)):
                #     try:
                #         c2, d2 = pos.unravel(N, M)
                #         print("  >", pos.x, pos.y, pos.direction, c2, d2)
                #         for item in af.input:
                #             i = _items.index(item)
                #             print("  =>", res.x[Xcdi[c2][d2][i]], item)
                #     except IndexError:
                #         pass
                for x2, y2 in af.occupied_region((x, y)):
                    try:
                        layout[y2][x2] = "#"
                        if af.facility.name == "pylon":
                            layout[y2][x2] = "%"
                        if (
                            x + 1 <= x2 < x - 1 + af.facility.width
                            and y + 1 <= y2 < y - 1 + af.facility.height
                        ):
                            layout[y2][x2] = "."
                    except IndexError:
                        pass
    # print("\n".join(["".join(x) for x in layout]))
    # print()

    for c, x, y in Cxy:
        z = ""
        for d in D:
            for i, item in enumerate(_items):
                if res.x[Xcdi[c][d][i]]:
                    print(f"- ({x}, {y}, #{c}) {'^>v<'[d]} {item}")
                    z += "^>v<"[d]
                    # layout[y][x] = "+" if len(z) >= 2 else z
                    for pre, post in (
                        ("^", "╻"),
                        (">", "╸"),
                        ("v", "╹"),
                        ("<", "╺"),
                        ("^>", "┓"),
                        (">v", "┛"),
                        ("v<", "┗"),
                        ("<^", "┏"),
                    ):
                        if set(z) == set(pre):
                            layout[y][x] = post

    print("\n".join(["".join(x) for x in layout]))
    print()


if __name__ == "__main__":
    # MARK: Test
    # solve((5, 5), {"originium_ore": 1})  # basic (sanity check)
    # solve((6, 5), {"originium_ore": 1})  # basic, non-square check
    # solve((7, 3), {"originium_ore": 1})  # basic, tighter
    # solve((3, 7), {"originium_ore": 1})  # basic, tighter, rotated
    # solve((9, 6), {"originium_ore": 2})  # multiple req
    # solve((9, 6), {"origocrust": 1})  # chained facility (no bend, no extend)
    # solve((6, 9), {"origocrust": 1})  # test rotations (facility input ports)
    # solve((9, 5), {"origocrust": 1})  # tight fit of above (no bend, no extend)
    # solve((8, 5), {"origocrust": 1})  # requires conveyor bend (from facil out)
    # solve((10, 3), {"origocrust": 1})  # conveyor extend
    # solve((3, 10), {"origocrust": 1})  # rotation should work
    solve((12, 13), {"buckflower": 1})  # plant loop
    # solve((13, 13), {"buckflower_powder": 1})  # plant loop with powder
    pass
