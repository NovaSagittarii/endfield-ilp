from pathlib import Path
from typing import Final, List, Tuple

import yaml

from akef.item import Item, ResourceCost
from akef.power_source import PowerSource


def to_wiki(snake_case: str) -> str:
    s = "_".join(w.capitalize() for w in snake_case.split("_"))
    return f"https://endfield.wiki.gg/images/thumb/{s}.png/72px-{s}.png"


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
        items[k] = Item(
            k, 2, ResourceCost.from_dict({k: 30}), [], "mine", output=1, icon=to_wiki(k)
        )
    # kinda fake values to make it calculate properly
    # an instance of a raw_resource represents one full belt of the item

    for k in _items:
        if k in raw_resources or k in items:
            continue
        u = _items[k]
        action: str = list(k for k in u.keys() if k != "value")[0]
        recipe: dict = u[action]

        value = u.get("value", 0)
        seconds = recipe.get("seconds", 2)
        quantity = recipe.get("quantity", 1)

        items[k] = Item(
            name=k,
            seconds_to_craft=seconds,
            action=action,
            overhead=actions[action],
            output=quantity,
            inputs=[],
            value=value,
            taints=u.get("taints", []),
            icon=u.get("icon", to_wiki(k)),
        )

    for name in _items:
        u = _items[name]
        action: str = list(k for k in u.keys() if k != "value")[0]
        recipe: dict = _items[name][action]
        prereqs: List[Tuple[str, int]] = []
        for item, amt in recipe.items():
            if item in ("seconds", "quantity"):
                continue
            prereqs.append((item, amt))

        for p, amt in prereqs:
            items[name].inputs_.append((amt, items[p]))
