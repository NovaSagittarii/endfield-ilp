import math

import streamlit as st

from akef.items import Item, ResourceCost, items, power_sources, raw_resources
from akeflp.solver import POWER, solve


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

    with st.expander(rateinfo):
        if item.inputs:
            st.write(f"to {item.action} costs {item.action_overhead}")
            for amt, pitem in item.inputs:
                recipe_rate = rate / item.output
                render(pitem, amt * recipe_rate, depth + 1)
        else:
            st.caption("This is a raw resource.")


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
    st.write(
        "If you scroll to the bottom, you can see how power and ore upkeep of "
        "each facility is calculated."
    )
    st.write("# Optimize")
    depot_size = st.number_input("Depot Size", step=1000, min_value=8000)
    checkin_interval_days = st.select_slider(
        "Check-in interval",
        [1 / 24, 1 / 12, 0.125, 0.25, 0.5, 1, 2, 3, 4, 5, 6, 7],
        1,
        lambda x: (f"{x} day" if x >= 1 else f"{round(x * 24)} hour")
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
            "power": ci2.number_input("PAC Power", step=1, min_value=200)
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
    with c1.popover("Objective function"):
        vals = {
            k: st.number_input(f"![]({v.icon}) {k}", step=1, value=v.value)
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
