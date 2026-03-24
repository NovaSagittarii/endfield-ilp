from typing import Final

from akef.power_source import PowerSource
from akef.recipe import Facility, Recipe
from akef.recipes import facilities as _facilities
from akef.recipes import power_sources as _power_sources
from akef.recipes import raw_resources as _raw_resources
from akef.recipes import recipes as _drecipes

facility_list: Final = [
    Facility(name=k, power=v["power"]) for k, v in _facilities.items()
]
"""all facilities, referenced by recipes"""
_facility_names: Final = [x.name for x in facility_list]
_facility_lookup: Final = {x.name: x for x in facility_list}

power_sources: Final[dict[str, PowerSource]] = {
    psrc.name: psrc for psrc in _power_sources
}
"""all power sources"""

raw_resources: Final[list[str]] = list(_raw_resources)
"""all raw resources, i.e. come from a ore vein"""

_items: list[str] = []
_recipes: list[Recipe] = []
for drecipe in _drecipes:
    method = drecipe.facility
    assert method in _facility_names, f"Facility {method} does not exist."
    _recipes.append(
        Recipe(
            facility=_facility_lookup[method],
            duration=drecipe.seconds,
            inputs=drecipe.inputs,
            outputs=drecipe.outputs,
        )
    )

    _items.extend(drecipe.inputs.keys())
    _items.extend(drecipe.outputs.keys())
_items.extend(raw_resources)


items: Final = tuple(set(_items))
"""all items, use .index(); can use dict[str, int] but there aren't that many strings"""

recipes: Final = tuple(_recipes)
"""all recipes"""
