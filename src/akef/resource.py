"""
Raw resources
"""

from __future__ import annotations

from typing import Final, Optional, TypeAlias

import numpy as np

from akef.data import _data

raw_resources: Final[list[str]] = list(_data["raw_resources"])
N: Final = len(raw_resources)
POWER: Final = raw_resources.index("power")

T: TypeAlias = np.ndarray


class ResourceCost:
    def __init__(self, val: Optional[T] = None) -> None:
        self.val: Final[T] = val if val is not None else np.zeros((N,), np.int16)

    @classmethod
    def from_dict(cls, d: dict) -> ResourceCost:
        val = np.zeros((N,), np.int16)
        for i, k in enumerate(raw_resources):
            val[i] = d.get(k, 0)
        return ResourceCost(val)

    def __repr__(self) -> str:
        return ", ".join(
            [
                (
                    f":blue[**{self.val[i]}**] {raw_resources[i]}/min"
                    if raw_resources[i] != "power"
                    else f":yellow[**{self.val[i]}**]W"
                )
                for i in range(N)
                if self.val[i]
            ]
        )

    def __add__(self, other: ResourceCost) -> ResourceCost:
        return ResourceCost(self.val + other.val)

    def __mul__(self, k: int) -> ResourceCost:
        return ResourceCost(self.val * k)
