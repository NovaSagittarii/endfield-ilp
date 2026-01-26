from pathlib import Path
from typing import Final, List, Tuple

import yaml

from akef.item import Item, ResourceCost
from akef.power_source import PowerSource

items = {}
with open(Path(__file__).resolve().parent / "items.yaml", "r") as file:
    _data: Final[dict] = yaml.safe_load(file.read())
    actions: Final[dict[str, ResourceCost]] = {
        k: ResourceCost.from_dict(v) for k, v in _data["actions"].items()
    }
    power_sources: Final[dict[str, PowerSource]] = {
        k: PowerSource.from_dict(v) for k, v in _data["power"].items()
    }
    raw_resources: Final[set[str]] = set(_data["raw_resources"])
    _items: Final[dict] = _data["items"]
    items: dict[str, Item] = {}

    for k in raw_resources:
        items[k] = Item(k, 60, ResourceCost.from_dict({k: 1}), [], 1)
        # kinda fake values to make it calculate properly

    def dfs(k: str) -> None:
        if k in raw_resources or k in items:
            return
        u = _items[k]
        action: Final[str] = list(k for k in u.keys() if k != "value")[0]
        recipe: Final[dict] = u[action]

        value = u.get("value", 0)
        seconds = recipe.get("seconds", 2)
        quantity = recipe.get("quantity", 1)
        prereqs: List[Tuple[str, int]] = []
        for item, amt in recipe.items():
            if item in ("seconds", "quantity"):
                continue
            prereqs.append((item, amt))
            dfs(item)
        items[k] = Item(
            name=k,
            seconds_to_craft=seconds,
            action=action,
            overhead=actions[action],
            output=quantity,
            inputs=[(amt, items[p]) for p, amt in prereqs],
            value=value,
            taints=u.get("taints", []),
        )

    for name in _items:
        dfs(name)
