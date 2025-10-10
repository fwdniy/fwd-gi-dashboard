import streamlit as st
from streamlit import session_state as ss
from grid import AgGridBuilder
from .forward import calculate_forward_rates, format_forward_rates

def build_forward_grid():
    if ss.selected_mode != 'Forward' or ss.selected_curve_forward is None:
        return

    df = ss.selected_curve_forward
    forward_dict = calculate_forward_rates(df)
    grid_df = format_forward_rates(forward_dict)

    grid = AgGridBuilder(grid_df)
    grid.add_columns(
        [col for col in grid_df.columns if col != 'Forward \ Tenor'],
        row_group=False,
        max_width=60
    )

    grid.show_grid(120 + 30 * len(grid_df))