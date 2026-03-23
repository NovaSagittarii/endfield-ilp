"""
PuLP-based plan solver with intermediate variables and cross-region transfer
"""

from typing import NamedTuple, cast

import pulp as lp

from akef.recipe_list import (
    PowerSource,
    Recipe,
    items,
    power_sources,
    recipes,
)
from akeflp.plan import Plan, PlanConstraints, RegionPlan, RegionPlanConstraints


class RegionVars(NamedTuple):
    flow: dict[str, lp.LpAffineExpression]
    """net rate of each item (convert to constraint at end)"""
    oplan: list[tuple[lp.LpVariable, lp.LpVariable, Recipe]]
    """output variables (Xalloc, Xactual_output, recipe)"""
    pplan: list[tuple[lp.LpVariable, PowerSource]]
    """power plan variables (Xusage, power_source)"""


def solve(config: PlanConstraints) -> Plan:
    model = lp.LpProblem("", lp.LpMaximize)
    objective = lp.LpAffineExpression()

    regions: dict[str, RegionVars] = {}
    for region in config.regions:
        regions[region.region_name] = RegionVars(
            flow={item: lp.LpAffineExpression() for item in items},
            oplan=[
                (
                    lp.LpVariable(
                        f"{region.region_name}_alloc_{i:03}",
                        lowBound=0,
                        upBound=None,
                        cat=lp.LpContinuous,
                    ),
                    lp.LpVariable(
                        f"{region.region_name}_output_{i:03}_"
                        + "+".join(recipe.outputs.keys()),  # for debug
                        lowBound=0,
                        upBound=None,
                        cat=lp.LpContinuous,
                    ),
                    recipe,
                )
                for i, recipe in enumerate(recipes)
            ],
            pplan=[
                (
                    lp.LpVariable(
                        f"{region.region_name}_fuel_{ps.name}",
                        lowBound=0,
                        upBound=None,
                        cat=lp.LpInteger,
                    ),
                    ps,
                )
                for ps in power_sources.values()
            ],
        )

    for region in config.regions:
        rflow = regions[region.region_name].flow
        """regional item flow"""

        oplan = regions[region.region_name].oplan
        """output variables (allocated, actual_output, recipe)"""

        pplan = regions[region.region_name].pplan
        """power variables (item_usage, power_source)"""

        # setup income
        for k, v in region.raw_income.items():
            rflow[k] += v  # raw income

        # power constraints
        net_power = region.base_power
        for x, ps in pplan:
            net_power += x * ps.power_output  # generate power
            rflow[ps.name] -= x * ps.consumption_rate  # consume for power
            if ps.name in region.value:
                objective -= x * ps.consumption_rate * region.value[ps.name]
        for alloc, _, recipe in oplan:
            net_power -= alloc * recipe.facility.power  # cost power
        model += net_power >= region.base_load

        # recipe effects on item net flow
        for alloc, output, recipe in oplan:
            model += output <= alloc  # allocation constraint
            for k, v in recipe.input_flow.items():
                rflow[k] -= v * output  # consume as input
            for k, v in recipe.output_flow.items():
                rflow[k] += v * output  # produce as output
        for item in items:
            if item in region.value:
                objective += region.value[item] * rflow[item]
                # sell off any excess

    for rvars in regions.values():
        for x in rvars.flow.values():
            model += x >= 0  # no negative net flow allowed
    model += objective
    # print(model)

    solver = lp.apis.HiGHS()
    model.solve(solver)

    facility_plan: dict[str, dict[str, int]] = {k: {} for k in regions.keys()}
    for region_name, region_plan in regions.items():
        cts = facility_plan[region_name]
        for alloc, _, recipe in region_plan.oplan:
            k = recipe.facility.name
            if k not in cts:
                cts[k] = 0
            cts[k] += round(cast(float, lp.value(alloc)))

    return Plan(
        [
            RegionPlan(
                config=region,
                recipe_plan=[
                    (recipe, cast(float, lp.value(alloc)))
                    for alloc, _, recipe in regions[region.region_name].oplan
                    if lp.value(alloc)
                ],
                facility_plan=facility_plan[region.region_name],
                power_plan={
                    ps.name: round(cast(float, lp.value(x)))
                    for x, ps in regions[region.region_name].pplan
                    if lp.value(x)
                },
                profit=cast(float, lp.value(objective)),
            )
            for region in config.regions
        ]
    )


if __name__ == "__main__":
    config = PlanConstraints(
        regions=[
            RegionPlanConstraints(
                region_name="test",
                raw_income={"originium_ore": 540},
                value={"origocrust": 10},
                base_power=1000,
                base_load=0,
            )
        ],
        max_cross_transfer_rate=0,
    )
    out = solve(config)
    print(out.regions, out.valid)
