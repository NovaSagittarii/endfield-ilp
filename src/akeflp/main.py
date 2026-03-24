"""
Streamlit interface for Resource Plan Solver
"""

import math

import streamlit as st

from akef.recipe_list import _facility_lookup, items, power_sources, raw_resources
from akeflp.plan import PlanConstraints, RegionPlanConstraints
from akeflp.plan_solver import solve


def region_editor(
    region_name: str,
    default_depot_size: int,
    facility_limit: dict[str, int],
    default_income: dict[str, int],
    default_value: dict[str, int],
) -> RegionPlanConstraints:
    with st.expander(f"{region_name} Constraints"):
        depot_size = st.number_input(
            "Depot Size",
            key=f"{region_name}_ds",
            step=1000,
            min_value=8000,
            value=default_depot_size,
        )
        checkin_interval_days = st.select_slider(
            "Check-in interval",
            key=f"{region_name}_ds1",
            help="How frequently will you sell items? This is used to determine "
            "what the max output rate of any item should be to prevent waste.",
            options=[1 / 24, 1 / 12, 0.125, 0.25, 0.5, 1, 2, 3, 4, 5, 6, 7],
            value=1,
            format_func=lambda x: (f"{x} day" if x >= 1 else f"{round(x * 24)} hour")
            + f" ({round(depot_size // (60 * 24 * x))}/min)",
        )
        max_rate = round(depot_size // (60 * 24 * checkin_interval_days))

        ci1, ci2 = st.columns((1, 1))

        with st.popover(
            "Objective function",
            help="Configure the 'value' of each item here. "
            "If you set an item to zero, the item won't be created for value. "
            "If you want a non-sellable item, put how much you think it is worth "
            "for the optimizer.",
        ):
            value = {
                k: st.number_input(
                    k, 0, 100, value=default_value.get(k, 0), key=f"{region_name}_{k}"
                )
                for k in items
            }

    return RegionPlanConstraints(
        region_name=region_name,
        raw_income={
            k: ci1.number_input(
                f"{k.replace('_', ' ').capitalize()}/min",
                0,
                value=default_income.get(k, 0),
                key=f"{region_name}_income_{k}",
            )
            for k in raw_resources
        },
        base_load=ci2.number_input(
            "Base load",
            key=f"{region_name}_bl",
            help="Total power usage from towers, relay, drills, etc.",
            step=1,
            min_value=0,
            value=1000,
        ),
        base_power=ci2.number_input(
            "PAC Power",
            key=f"{region_name}_bp",
            help="Base power supplied by the main PAC. "
            "You probably don't have to change this.",
            step=1,
            min_value=200,
        ),
        max_net_output=max_rate,
        value=value,
        facility_limit=facility_limit,
    )


def main() -> None:
    st.title("Endfield ILP Optimizer")
    st.write(
        "Put your ore income and baseline power needs in the box. The program "
        "will calculate what facilities you can have and a valid way of "
        "powering everything such that the **objective** is maximized."
    )
    st.write(
        "**Objective** is defined as giving every item a score and trying "
        "to maximize the score per hour you can get. The preset setting is "
        "maximizing the amount Stock Bill you can get, assuming you were able "
        "to sell everything (unlikely to be true)."
    )
    st.write("# Optimize")
    plan_constraints = PlanConstraints(
        regions=[
            region_editor(
                "Valley IV",
                facility_limit={"skyforge": 0, "pump": 0},
                default_depot_size=80000,
                default_income={
                    "originium_ore": 560,
                    "amethyst_ore": 240,
                    "ferrium_ore": 1080,
                },
                default_value={
                    "hc_valley_battery": 70,
                    "sc_valley_battery": 30,
                    "lc_valley_battery": 16,
                    "buck_capsule_a": 70,
                    "canned_citrome_a": 70,
                    "canned_citrome_b": 27,
                    "buck_capsule_b": 27,
                    "canned_citrome_c": 10,
                    "buck_capsule_c": 10,
                    "amethyst_bottle": 2,
                    "origocrust": 1,
                    "amethyst_part": 1,
                    "ferrium_part": 1,
                    "steel_part": 3,
                },
            ),
            region_editor(
                "Wuling",
                facility_limit={
                    "skyforge": st.number_input(
                        "wuling skyforges", min_value=0, value=3
                    )
                },
                default_depot_size=58000,
                default_income={
                    "originium_ore": 480,
                    "ferrium_ore": 90,
                    "cuprium_ore": 120,
                },
                default_value={
                    "cuprium_part": 1,
                    "yazhen_syringe_a": 22,
                    "sc_wuling_battery": 54,
                    "lc_wuling_battery": 25,
                    "jincao_drink": 16,
                    "yazhen_syringe_c": 16,
                    "xiranite": 1,
                },
            ),
        ],
        max_cross_transfer_rate=st.number_input(
            "manual transfer rate",
            help="How much you manually transfer via Dijiang. This is tedious.",
            min_value=0,
        ),
    )

    # if not st.button("Solve (takes a while)"):
    #     return

    with st.spinner("Running solver, please wait.", show_time=True):
        res = solve(plan_constraints)

    for region, c in zip(res.regions, st.columns([1 for _ in res.regions])):
        config = region.config
        c.write(f"## {config.region_name}")
        c.write(f"### Value rate: :green[**{region.profit:.2f}**]/min")

        power_generated = 0
        power_required = 0
        for k, v in region.power_plan.items():
            power_generated += power_sources[k].power_output * v
        for k, v in region.facility_plan.items():
            power_required += _facility_lookup[k].power * v

        with c.expander(
            f"Power :yellow[**{power_generated + config.base_power}**]W "
            + f" for load of :yellow[**{power_required + config.base_load}**]W ",
            expanded=True,
        ):
            st.caption(
                "Running at a time means how many thermal banks are currently "
                "used that as a fuel source. The power plan is tuned to "
                "minimize resources used to power the base, as those can be used "
                "to make other items."
            )
            for k, v in region.power_plan.items():
                ps = power_sources[k]
                st.write(
                    f"**{k}**: {v} at a time",
                    f"(:red[{v * ps.consumption_rate}]/min),",
                    (
                        f"generating :yellow[**{v * ps.power_output}**]W in total. "
                        # + f"Opportunity cost of :red[**{vp.opportunity_cost}**] "
                        # + "val/min."
                        if v
                        else ""
                    ),
                )
        with c.expander(
            f"Production using :yellow[**{power_required}**]W", expanded=False
        ):
            for recipe, utilization in region.recipe_plan:
                st.write(
                    f"{utilization:.2f}/{math.ceil(utilization)} "
                    + f"**{recipe.facility.name}** "
                    + f"{recipe.inputs} -> {recipe.outputs}"
                )
        with c.expander("Sell Plan", expanded=True):
            for k, v in region.sell_plan.items():
                st.write(f"{v:.2f}/min {k} :green[{config.value[k] * v:.1f}]/min")
