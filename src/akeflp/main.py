import math

import streamlit as st

from akef.items import Item, ResourceCost, items, power_sources, raw_resources
from akeflp.solver import POWER, solve


def render(item: Item, rate: float, depth: int = 0) -> None:
    totcost = item.cost * math.ceil(rate / item.base_rate)
    rateinfo = (
        f"{rate/item.output_rate:.3f}x "
        f'{(f"![icon]({item.icon})" if item.icon else "")}'
        f"{item.name} @ {rate}/min "
        f"$\\xleftarrow{{\\text{{costs}}}}$ {totcost} "
        + (f"[{item.value}]" if item.value else "")
    )
    if not item.inputs:
        st.write(rateinfo)
        return
    with st.expander(rateinfo):
        st.write(f"to {item.action} costs {item.action_overhead}")
        for amt, pitem in item.inputs:
            recipe_rate = rate / item.output
            render(pitem, amt * recipe_rate, depth + 1)


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
    constraints = ResourceCost.from_dict(
        {
            "originium_ore": st.number_input("Originium ore/min", step=1, min_value=0),
            "amethyst_ore": st.number_input("Amethyst ore/min", step=1, min_value=0),
            "ferrium_ore": st.number_input("Ferrium ore/min", step=1, min_value=0),
            "power": st.number_input("PAC Baseline power", step=1, min_value=200)
            - (
                baseline := st.number_input(
                    "Baseline power usage (Tower, relay, etc.)",
                    step=1,
                    min_value=0,
                    value=200,
                )
            ),
        }
    )
    allow_wuling = st.selectbox("Planet", ["Valley IV", "Wuling"]) == "Wuling"
    with st.expander("Objective function"):
        vals = {
            k: st.number_input(k, step=1, value=v.value)
            for k, v in items.items()
            if k not in raw_resources
        }
    if st.button("Calculate"):
        # st.write(constraints.__repr__(), constraints.val)
        # st.write(vals)
        try:
            res = solve(constraints, vals, [] if allow_wuling else ["wuling"])
            st.write(f"### Value rate: :green[**{res.value_rate}**]/min")
            with st.expander(
                f"### Power :yellow[**{res.power_total + baseline}**]W "
                + f" for load of :yellow[**{res.power_required + baseline}**]W "
                + f"({res.power_required}req + {baseline}base)",
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
            st.error("No solution found?? :/ (it should say something...)")

    st.write("# Resources")
    items_display = list(items.values())
    match st.selectbox("Sort by", ["Default", "Power (dec)", "Value (dec)"], index=1):
        case "Default":
            pass
        case "Power (dec)":
            items_display.sort(key=lambda x: x.cost.val[POWER], reverse=True)
        case "Value (dec)":
            items_display.sort(key=lambda x: x.value, reverse=True)
    for item in items_display:
        if item.name in raw_resources:
            continue
        render(item, item.base_rate * item.output)
