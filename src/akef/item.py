from __future__ import annotations

import math
from typing import Final, Sequence, Tuple, TypeAlias

from akef.resource import ResourceCost

Rate: TypeAlias = int  # items per minute


class Item:
    def __init__(
        self,
        name: str,
        seconds_to_craft: int,
        overhead: ResourceCost,
        inputs: Sequence[Tuple[int, Item]],
        action: str,
        output: int = 1,
        value: int = 1,
        taints: Sequence[str] = [],
        icon: str | None = None,
    ) -> None:
        self.name: Final = name
        self.base_rate: Final = 60 / seconds_to_craft
        """how many completions per minute"""

        self.cost: Final[ResourceCost] = sum(
            [
                item.cost
                * math.ceil(w * self.base_rate / (item.base_rate * item.output))
                for w, item in inputs
            ],
            overhead,
        )
        self.output: Final = output
        self.inputs: Final = inputs
        self.action: Final = action
        self.action_overhead: Final = overhead
        self.value: Final = value
        self.output_rate: Final = self.base_rate * self.output
        """how much one facility can output per minute (base_rate * output)"""

        all_taints = set(taints)
        for _, item in inputs:
            all_taints |= item.taints
        self.taints: Final = all_taints

        self.icon: Final = icon
