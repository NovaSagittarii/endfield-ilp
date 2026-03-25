"""
Streamlit interface for Resource Plan Solver
"""

import base64

import graphviz  # type: ignore
import PIL
import streamlit as st
from streamlit.components.v1 import html

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
        regional_multiplier = st.number_input(
            "Regional Multiplier", 0.0, None, 1.0, key=f"{region_name}_mult"
        )

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
                * regional_multiplier
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
                        "wuling skyforges", min_value=0, value=4
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

    st.caption(
        "Running at a time means how many thermal banks are currently "
        "used that as a fuel source. The power plan is tuned to "
        "minimize resources used to power the base, as those can be used "
        "to make other items."
    )
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
            for k, v in region.power_plan.items():
                ps = power_sources[k]
                st.write(
                    f"**{k}**: {v} thermal banks",
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
            for recipe, utilization, alloc in region.recipe_plan:
                st.write(
                    f"{utilization:.2f}/{alloc} "
                    + f"**{recipe.facility.name}** "
                    + f"{recipe.inputs} -> {recipe.outputs}"
                )
        if len(region.sell_plan):
            with c.expander("Sell Plan", expanded=True):
                for k, vf in sorted(
                    list(region.sell_plan.items()),
                    key=lambda k: (-config.value[k[0]], k),
                ):
                    w = config.value[k]
                    st.write(f"{vf:.2f}/min {k} :gray[({w})] :green[{w * vf:.1f}]/min")
        if sum(len(x) for x in region.cross_transfer.values()):
            with c.expander("Transfer Plan"):
                for dest, plan in region.cross_transfer.items():
                    with st.expander(f"To {dest}", expanded=True):
                        for k, vf in plan.items():
                            st.write(f"{vf:.2f}/min {k}")

    with st.spinner("Rendering graph...", show_time=True):
        graph = graphviz.Digraph(engine="patchwork")
        # graph.attr(overlap="false")
        # graph.attr(splines="true")
        # graph.attr(sep="0.1")
        # graph.attr(pack="true")
        region_to_idx = {
            region.config.region_name: ri for ri, region in enumerate(res.regions)
        }
        for ri, region in enumerate(res.regions):
            config = region.config
            with graph.subgraph(name=f"cluster_{ri}") as c:
                c.attr(
                    style="rounded",
                    color="blue",
                    label=config.region_name,
                    fontsize="16",
                )

                item_nodes: set[str] = set()
                c.node(cn_sell := f"{ri}sell", "sell", shape="square", color="green")
                c.node(cn_fuel := f"{ri}fuel", "thermal_bank", shape="square")
                for k, v in region.power_plan.items():
                    if v:
                        vf = v * power_sources[k].consumption_rate
                        item_nodes.add(uid := f"{ri}+{k}")
                        c.edge(uid, cn_fuel, f"{vf:.2f}")
                for k, v in region.sell_plan.items():
                    if v:
                        item_nodes.add(uid := f"{ri}+{k}")
                        c.edge(uid, cn_sell, f"{v:.2f}")

                for i, recipe_stats in enumerate(region.recipe_plan):
                    recipe, utilization, alloc = recipe_stats
                    if utilization < 1e-10:
                        continue
                    c.node(
                        f"{ri}r{i}",
                        (
                            f"{utilization:.2f}/{alloc} {recipe.facility.name}"
                            if utilization + 1e-6 < alloc
                            else f"{alloc} {recipe.facility.name}"
                        ),
                        xlabel="<<FONT COLOR='gray' POINT-SIZE='10'>"
                        + f"{recipe.duration}s"
                        + "</FONT>>",
                        shape="diamond",
                        color="red",
                        margin="0",
                        width="0.3",
                        height="0.3",
                        # fontsize="10",
                        fixedsize="true",
                    )
                    for k, v in recipe.input_flow.items():
                        item_nodes.add(f"{ri}+{k}")
                        c.edge(
                            f"{ri}+{k}",
                            f"{ri}r{i}",
                            f"{v * utilization:.2f}",
                            headlabel=f"{recipe.inputs[k]}",
                            labelcolor="gray",
                            labelfontsize="8",
                            labeldistance="1.5",
                        )
                    for k, v in recipe.output_flow.items():
                        item_nodes.add(f"{ri}+{k}")
                        c.edge(
                            f"{ri}r{i}",
                            f"{ri}+{k}",
                            f"{v * utilization:.2f}",
                            taillabel=f"{recipe.outputs[k]}",
                            labelcolor="gray",
                            labelfontsize="8",
                            labeldistance="1.5",
                        )
                for k in item_nodes:
                    c.node(k, k.split("+")[1].replace("_", " ").capitalize())

        for ri, region in enumerate(res.regions):
            for dest, flows in region.cross_transfer.items():
                di = region_to_idx[dest]
                for k, v in flows.items():
                    graph.edge(
                        f"{ri}+{k}",
                        f"{di}+{k}",
                        taillabel=f"{v:.2f}",
                        headlabel=f"{v:.2f}",
                        color="orange",
                        fontcolor="red",
                    )

        # st.graphviz_chart(graph, use_container_width=True)
        graph.attr(dpi="300")
        src = graphviz.Source(graph.source)
        try:
            st.image(src.pipe(format="webp", quiet=True))
        except PIL.UnidentifiedImageError:
            st.error("Cannot render as webp")

        import re

        svg_bytes = src.pipe(format="svg", quiet=True)
        svg = svg_bytes.decode()
        svg = re.sub(r'width="[\d\.]+pt"', "", svg)
        svg = re.sub(r'height="[\d\.]+pt"', "", svg)
        svg = re.sub(
            r"<svg([^>]*)>",
            r'<svg\1 style="width:100%; height:100%; display:block;">',
            svg,
        )

        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script
            src="https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js"
            >
            </script>
        </head>
        <body style="width:100%; height:100vh; margin:0;">
            {svg}
            <script>
            svgPanZoom('svg', {{
                zoomEnabled: true,
                controlIconsEnabled: true,
                fit: true,
                center: true,
                minZoom: 0.001,
            }});
            </script>
        </body>
        </html>
        """
        html(html_code, height=800)

        st.download_button(
            label="Download SVG",
            data=svg_bytes,
            file_name="flows.svg",
            mime="image/svg+xml",
        )

        def open_html_in_new_tab(
            html_code: str, button_label: str = "View in New Tab"
        ) -> None:
            """
            LLM-generated method to open the svg pan-zoom in a new tab so
            it is easier to explore.
            """
            b64_html = base64.b64encode(html_code.encode()).decode()
            js_snippet = f"""
                <script>
                function openHtml() {{
                    const htmlContent = atob("{b64_html}");
                    const blob = new Blob([htmlContent], {{ type: 'text/html' }});
                    const url = URL.createObjectURL(blob);
                    window.open(url, '_blank');
                }}
                </script>
                <button onclick="openHtml()" style="
                    background-color: #00acee;
                    color: white;
                    border: none;
                    padding: 0.5rem 1rem;
                    border-radius: 0.5rem;
                    cursor: pointer;
                    font-family: sans-serif;
                    font-weight: 500;">
                    {button_label}
                </button>
            """
            html(js_snippet)

        open_html_in_new_tab(html_code, "View svg in new tab")
