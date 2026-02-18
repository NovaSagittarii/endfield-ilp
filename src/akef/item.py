from __future__ import annotations

import math
from typing import Final, MutableSequence, Sequence, Tuple, TypeAlias

from akef.resource import ResourceCost

Rate: TypeAlias = int  # items per minute


class Item:
    def __init__(
        self,
        name: str,
        seconds_to_craft: int,
        overhead: ResourceCost,
        inputs: MutableSequence[Tuple[int, Item]],
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
        """
        NOTE: this value is correct since inputs can have loops, so currently,
            it is not being calculated.
        """

        self.output: Final = output
        self.inputs: Final[Sequence[Tuple[int, Item]]] = inputs
        self.inputs_: Final[MutableSequence[Tuple[int, Item]]] = (
            inputs  # the one you can edit (usually you shouldn't though)
        )
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
