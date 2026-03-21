from pathlib import Path
from typing import Final

import yaml

with open(Path(__file__).resolve().parent / "items.yaml", "r") as file:
    _data: Final[dict] = yaml.safe_load(file.read())
