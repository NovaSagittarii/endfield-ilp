"""
Would've been items.yaml but it turns out recipes can have multiple outputs in 1.1
This wasn't true in 1.0 :c

Anyways, I used python to generate what would've been the yaml to use templates to
generate some of the items.

Naming convention:
- items are python-style snake-case (symbols removed, spaces normalized)
- facilities are referred as their present-tense verb form (easier to type)
"""

from typing import Final, NamedTuple

from akef.power_source import PowerSource

raw_resources: Final = (
    "originium_ore",
    "amethyst_ore",
    "ferrium_ore",
    "cuprium_ore",
)

power_sources: Final = (
    PowerSource("originium_ore", 8, 50),
    PowerSource("lc_valley_battery", 40, 220),
    PowerSource("sc_valley_battery", 40, 420),
    PowerSource("hc_valley_battery", 40, 1100),
    PowerSource("lc_wuling_battery", 40, 1600),
    PowerSource("sc_wuling_battery", 40, 3200),
)

facilities: Final = {
    "refine": {"power": 5},
    "shred": {"power": 5},
    "fit": {"power": 20},
    "mold": {"power": 10},
    "plant": {"power": 20},
    "seed": {"power": 10},
    "gear": {"power": 10},
    "fill": {"power": 20},
    "pack": {"power": 20},
    "grind": {"power": 50},
    "crucible": {"power": 50},
    "skyforge": {"power": 50},
    "pump": {"power": 10},
    "treatment": {"power": 50},
}


class RecipeData(NamedTuple):
    """
    ```yaml
    - facility: !!str
      inputs:
        [item_name]: !!int [amount]
      outputs:
        [item_name]: !!int [amount]
      seconds: (defaults to 2)
    ```
    """

    facility: str
    inputs: dict[str, int]
    outputs: dict[str, int]
    seconds: int = 2


_recipes: list[RecipeData] = []

# MARK: refine
for u, v in (
    ("ferrium_ore", "ferrium"),
    ("amethyst_ore", "amethyst_fiber"),
    ("originium_ore", "origocrust"),
    ("dense_origocrust_powder", "packed_origocrust"),
    ("dense_ferrium_powder", "steel"),
    ("cryston_powder", "cryston_fiber"),
    ("dense_carbon_powder", "stabilized_carbon"),
    ("dense_originium_powder", "dense_origocrust_powder"),
    # omit Valley IV plants to carbon since unused
):
    _recipes.append(
        RecipeData(
            facility="refine",
            inputs={u: 1},
            outputs={v: 1},
        )
    )
for u, v, w in (
    ("jincao", "carbon", 2),
    ("yazhen", "carbon", 2),
):
    _recipes.append(
        RecipeData(
            facility="refine",
            inputs={u: 1},
            outputs={v: w},
        )
    )
_recipes.append(
    RecipeData(
        facility="refine",
        inputs={"cuprium_ore": 1, "clean_water": 1},
        outputs={"cuprium": 1, "sewage": 1},
    )
)

# MARK: shred
for item, amt in {
    "cuprium": 1,
    "ferrium": 1,
    "amethyst_fiber": 1,
    "originium_ore": 1,
    "carbon": 2,
    "origocrust": 1,
    "buckflower": 2,
    "citrome": 2,
    "sandleaf": 3,
    "aketine": 2,
    "jincao": 2,
    "yazhen": 2,
}.items():
    output = item.split("_")[0] + "_powder"
    _recipes.append(
        RecipeData(facility="shred", inputs={item: 1}, outputs={output: amt})
    )

# MARK: fit, mold
_refined = ("ferrium", "amethyst_fiber", "steel", "cryston_fiber", "cuprium")
for item in _refined:
    material = item.split("_")[0]
    output = material + "_part"
    _recipes.append(RecipeData(facility="fit", inputs={item: 1}, outputs={output: 1}))
    output = material + "_bottle"
    _recipes.append(RecipeData(facility="mold", inputs={item: 2}, outputs={output: 1}))

# MARK: plant, seed
_stdplant = ("buckflower", "citrome", "sandleaf", "aketine")
_liqplant = ("jincao", "yazhen")
for item in _stdplant:
    _recipes.append(
        RecipeData(facility="plant", inputs={(item + "_seed"): 1}, outputs={item: 1})
    )
    _recipes.append(
        RecipeData(facility="seed", inputs={item: 1}, outputs={(item + "_seed"): 2})
    )
for item in _liqplant:
    _recipes.append(
        RecipeData(
            facility="plant",
            inputs={(item + "_seed"): 1, "clean_water": 1},
            outputs={item: 2},
        )
    )
    _recipes.append(
        RecipeData(
            facility="seed",
            inputs={item: 1},
            outputs={(item + "_seed"): 1},
        )
    )

# MARK: treatment
treatable_liquids = ("sewage", "xircon_effluent", "inert_xircon_effluent")
for liq in treatable_liquids:
    _recipes.append(RecipeData(facility="treatment", inputs={liq: 1}, outputs={}))

# MARK: gear
_comps = {
    "amethyst": (("origocrust", 5), ("amethyst_fiber", 5)),
    "ferrium": (("origocrust", 10), ("ferrium", 10)),
    "cryston": (("packed_origocrust", 10), ("cryston_fiber", 10)),
    "xiranite": (("packed_origocrust", 10), ("xiranite", 10)),
    "cuprium": (("cuprium_part", 10), ("xiranite", 10)),
}
for item, inp in _comps.items():
    _recipes.append(
        RecipeData(
            facility="gear",
            inputs={k: v for k, v in inp},
            outputs={(item + "_component"): 1},
            seconds=10,
        )
    )

# MARK: fill
for item, out in (
    ("citrome", "canned_citrome_"),
    ("buckflower", "buck_capsule_"),
):
    _recipes.extend(
        (
            RecipeData(
                facility="fill",
                inputs={"amethyst_bottle": 5, f"{item}_powder": 5},
                outputs={f"{out}c": 1},
                seconds=10,
            ),
            RecipeData(
                facility="fill",
                inputs={"ferrium_bottle": 10, f"{item}_powder": 10},
                outputs={f"{out}b": 1},
                seconds=10,
            ),
            RecipeData(
                facility="fill",
                inputs={"steel_bottle": 10, f"ground_{item}_powder": 10},
                outputs={f"{out}a": 1},
                seconds=10,
            ),
        )
    )
for item in ("ferrium", "cuprium"):
    for plant in _liqplant:
        bottle = f"{item}_bottle"
        liq = f"{plant}_solution"
        bottled = f"{bottle}_{liq}"
        _recipes.append(
            RecipeData(
                facility="fill",
                inputs={bottle: 1, liq: 1},
                outputs={bottled: 1},
            )
        )


# MARK: pack
_packings = {
    "industrial_explosive": (("amethyst_part", 5), ("aketine_powder", 1)),
    "lc_valley_battery": (("amethyst_part", 5), ("originium_powder", 10)),
    "sc_valley_battery": (("ferrium_part", 10), ("originium_powder", 15)),
    "hc_valley_battery": (("steel_part", 10), ("dense_originium_powder", 15)),
    "yazhen_syringe_c": (("ferrium_part", 10), ("ferrium_bottle_yazhen_solution", 5)),
    "yazhen_syringe_a": (("cuprium_part", 10), ("cuprium_bottle_yazhen_solution", 5)),
    "jincao_drink": (("ferrium_part", 10), ("ferrium_bottle_jincao_solution", 5)),
    "jincao_tea": (("cuprium_part", 10), ("cuprium_bottle_jincao_solution", 5)),
    "lc_wuling_battery": (("xiranite", 5), ("dense_originium_powder", 15)),
    "sc_wuling_battery": (("xircon", 5), ("dense_originium_powder", 20)),
}
for item, inp in _packings.items():
    _recipes.append(
        RecipeData(
            facility="pack",
            inputs={k: v for k, v in inp},
            outputs={item: 1},
            seconds=10,
        )
    )

# MARK: grind
_powders = {
    "amethyst_powder": "cryston_powder",
    **{
        f"{u}_powder": f"dense_{u}_powder"
        for u in ("ferrium", "originium", "carbon", "origocrust")
    },
    **{f"{u}_powder": f"ground_{u}_powder" for u in ("buckflower", "citrome")},
}
for u, v in _powders.items():
    _recipes.append(
        RecipeData(
            facility="grind",
            inputs={"sandleaf_powder": 1, u: 2},
            outputs={v: 1},
        )
    )

# MARK: crucible
for item in _liqplant:
    _recipes.append(
        RecipeData(
            facility="crucible",
            inputs={"clean_water": 1, f"{item}_powder": 1},
            outputs={f"{item}_solution": 1},
        )
    )
_recipes.append(
    RecipeData(
        facility="crucible",
        inputs={"clean_water": 1, "xiranite": 1},
        outputs={"liquid_xiranite": 1},
    )
)
_recipes.append(
    RecipeData(
        facility="crucible",
        inputs={"liquid_xiranite": 1, "sewage": 1},
        outputs={"xircon_effluent": 1, "inert_xircon_effluent": 1},
    )
)
_recipes.append(
    RecipeData(
        facility="crucible",
        inputs={"xircon_effluent": 2, "ferrium_powder": 1},
        outputs={"xircon": 1, "sewage": 1},
    )
)

_recipes.append(
    RecipeData(
        facility="skyforge",
        inputs={"stabilized_carbon": 2, "clean_water": 1},
        outputs={"xiranite": 1},
    )
)

# MARK: pump (water)
_recipes.append(
    RecipeData(
        facility="pump",
        inputs={},
        outputs={"clean_water": 1},
        seconds=1,
    )
)

recipes: Final = tuple(_recipes)
