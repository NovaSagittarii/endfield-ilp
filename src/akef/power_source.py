from __future__ import annotations

from typing import Final


class PowerSource:
    def __init__(self, name: str, duration_seconds: int, power_output: int) -> None:
        self.name: Final = name
        self.duration_seconds: Final = duration_seconds
        self.power_output: Final = power_output
        self.consumption_rate: Final = 60 / duration_seconds
        """how many units of the power source are consumed per minute for each
        active instance of the power source"""

    @classmethod
    def from_dict(cls, d: dict) -> PowerSource:
        return PowerSource("", duration_seconds=d["seconds"], power_output=d["power"])
