"""
Streamlit interface for Resource Plan Solver
"""

import math

import streamlit as st

from akef.items import Item, ResourceCost, items, power_sources, raw_resources
from akeflp.solver import POWER, TaskDetail, solve


def render(item: Item, rate: float, depth: int = 0) -> None:
    instances = math.ceil(rate / item.base_rate)
    totcost = item.cost * instances
    rateinfo = (
        f"{rate/item.output_rate:.3f}x "
        f'{(f"![icon]({item.icon})" if item.icon else "") * instances}'
        f"{item.name} @ {rate}/min "
        f"$\\xleftarrow{{\\text{{costs}}}}$ {totcost} "
        + (f"[{item.value}]" if item.value else "")
    )

    left, right = st.columns([2, 20])
    if item.icon:
        left.image(item.icon, width=36)
    with right.expander(rateinfo):
        if item.inputs:
            st.write(f"to {item.action} costs {item.action_overhead}")
            for amt, pitem in item.inputs:
                recipe_rate = rate / item.output
                render(pitem, amt * recipe_rate, depth + 1)
        else:
            st.caption("This is a raw resource.")


def main() -> None:
    st.write(
        "If you scroll to the bottom, you can see how power and ore upkeep of "
        "each facility is calculated. "
    )
    st.warning("This overestimates costs slightly, and doesn't do partial utilization.")
    st.write("# Optimize")
    depot_size = st.number_input("Depot Size", step=1000, min_value=8000)
    checkin_interval_days = st.select_slider(
        "Check-in interval",
        help="How frequently will you sell items? This is used to determine "
        "what the max output rate of any item should be to prevent waste.",
        options=[1 / 24, 1 / 12, 0.125, 0.25, 0.5, 1, 2, 3, 4, 5, 6, 7],
        value=1,
        format_func=lambda x: (f"{x} day" if x >= 1 else f"{round(x * 24)} hour")
        + f" ({round(depot_size // (60 * 24 * x))}/min)",
    )
    max_rate = round(depot_size // (60 * 24 * checkin_interval_days))
    st.write(f"Max output rate (to fill depot in 24 hours): :blue[**{max_rate}**]/min")
    c1, c2 = st.columns((1.1, 2))
    ci1, ci2 = c1.columns((1, 1))
    allow_wuling = ci2.selectbox("Planet", ["Valley IV", "Wuling"]) == "Wuling"
    constraints = ResourceCost.from_dict(
        {
            "originium_ore": ci1.number_input("Originium ore/min", step=1, min_value=0),
            "amethyst_ore": ci1.number_input("Amethyst ore/min", step=1, min_value=0),
            "ferrium_ore": ci1.number_input("Ferrium ore/min", step=1, min_value=0),
            "forge_of_the_sky": (
                ci1.number_input(
                    "Forges of the Sky",
                    step=1,
                    min_value=0,
                    max_value=4,
                    value=2,
                )
                if allow_wuling
                else 0
            )
            * 30,
            "power": ci2.number_input(
                "PAC Power",
                help="Base power supplied by the main PAC. "
                "You probably don't have to change this.",
                step=1,
                min_value=200,
            )
            - (
                baseline := ci2.number_input(
                    "Base load",
                    help="Total power usage from towers, relay, drills, etc.",
                    step=1,
                    min_value=0,
                    value=200,
                )
            ),
        }
    )
    with c1.popover(
        "Objective function",
        help="Configure the 'value' of each item here. "
        "If you set an item to zero, the item won't be created for value. "
        "If you want a non-sellable item, put how much you think it is worth "
        "for the optimizer.",
    ):

        def quantity_of_item(x: Item) -> TaskDetail:
            left, right = st.columns([3, 20])
            if x.icon:
                left.write("")
                left.write("")
                left.image(x.icon)
            return TaskDetail(
                value=right.number_input(
                    f"![]({x.icon}) {x.name}", step=1, value=x.value
                ),
                lower_bound=0,
                upper_bound=10000,
            )

        vals = {
            k: quantity_of_item(v)
            for k, v in sorted(items.items(), key=lambda x: x[1].name)
            if k not in raw_resources
        }
    try:
        res = solve(
            constraints=constraints,
            tasks=vals,
            max_rate=max_rate,
            disallowed_taints=[] if allow_wuling else ["wuling"],
        )
        c2.write(f"### Value rate: :green[**{res.value_rate}**]/min")
        with c2.expander(
            f"### Power :yellow[**{res.power_total + baseline}**]W "
            + f" for load of :yellow[**{res.power_required + baseline}**]W "
            + f"({res.power_required}req + {baseline}base)",
            expanded=True,
        ):
            st.caption(
                "Running at a time means how many thermal banks are currently "
                "used that as a fuel source. The power plan is tuned to "
                "minimize resources used to power the base, as those can be used "
                "to make other items."
            )
            for k, vp in res.power.items():
                st.write(
                    f"**{k}**: {vp.x} at a time",
                    f"(:red[{vp.x * power_sources[k].consumption_rate}]/min),",
                    (
                        f"generating :yellow[**{vp.power}**]W in total. "
                        + f"Opportunity cost of :red[**{vp.opportunity_cost}**] "
                        + "val/min."
                        if vp.x
                        else ""
                    ),
                )
        with st.expander("### Produce these items"):
            for k, vt in res.produce.items():
                item = items[k]
                st.write(
                    f"**{k}** @ {vt.x * item.output_rate}/min",
                    f"generating :green[**{vt.rate}**] value/min",
                )
                render(item, vt.x * item.output_rate)
    except TypeError:
        c2.error("No solution found?? :/ (it should say something...)")

    st.write("# Resources")
    items_display = list(items.values())
    match st.selectbox("Sort by", ["Alphabetical", "Power (dec)", "Value (dec)"]):
        case "Default":
            pass
        case "Power (dec)":
            items_display.sort(key=lambda x: x.cost.val[POWER], reverse=True)
        case "Value (dec)":
            items_display.sort(key=lambda x: x.value, reverse=True)
        case "Alphabetical":
            items_display.sort(key=lambda x: x.name)
    for item in items_display:
        if item.name in raw_resources:
            continue
        render(item, item.base_rate * item.output)
