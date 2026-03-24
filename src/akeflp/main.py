"""
Streamlit interface for Resource Plan Solver
"""

import streamlit as st

# from akeflp.v1 import main as main_v1
from akeflp.v2 import main as main_v2


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

    main_v2()
    # oops i broke v1 with modifiying how costs are calculated (for layout solver)
    # revisions = {"v1": main_v1, "v2": main_v2}
    # # tabs are not lazy
    # # for tab, body in zip(
    # #     st.tabs(list(revisions.keys()), default="v2"),
    # #     revisions.values(),
    # # ):
    # #     with tab:
    # #         body()
    # revisions[st.selectbox("Version", revisions.keys(), index=len(revisions) - 1)]()
