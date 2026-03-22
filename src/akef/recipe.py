"""
Recipe-oriented representation instead of item-oriented representation.

Probably should've gone with this way, but oh well.
"""

from typing import Final, NamedTuple, Sequence, TypeAlias

ItemBatch: TypeAlias = dict[str, int]
ItemFlow: TypeAlias = dict[str, float]


class Facility(NamedTuple):
    name: str
    power: int
    """power usage per unit"""


class Recipe:
    """
    inputs/outputs are per recipe instance
    input_flow/output_flow are per time unit
    """

    def __init__(
        self,
        facility: Facility,
        duration: int,
        inputs: ItemBatch,
        outputs: ItemBatch,
        taints: Sequence[str] = [],
    ) -> None:
        self.facility: Final = facility
        self.inputs: Final = inputs
        self.outputs: Final = outputs
        self.duration: Final = duration
        """seconds to craft item"""

        base_rate: Final = 60 / duration
        """completions per minute"""

        self.input_flow: ItemFlow = {k: v * base_rate for k, v in inputs.items()}
        self.output_flow: ItemFlow = {k: v * base_rate for k, v in outputs.items()}
        self.taints: Final[Sequence[str]] = taints
