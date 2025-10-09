import streamlit as st
from streamlit import session_state as ss
from grid import AgGridBuilder
from .data import build_spot_df, convert_floats_to_tenor
import pandas as pd

DISPLAY_TENORS = [0, 0.25, 0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30]

def build_forward_grid():
    if ss.selected_mode != 'Forward' or ss.selected_curve_forward is None:
        return

    df = ss.selected_curve_forward
    grid_df = _calculate_forward_rates(df)

    grid = AgGridBuilder(grid_df)
    grid.add_columns(
        [col for col in grid_df.columns if col != 'Forward \ Tenor'],
        row_group=False,
        max_width=60
    )

    grid.show_grid(120 + 30 * len(grid_df))

def _calculate_forward_rates(df):
    values, tenors, rates = build_spot_df(df)
    tenor_rates = dict(zip(tenors, rates))
    tenor_rates_forward = {}

    for tenor, rate in tenor_rates.items():
        if tenor == 0 or tenor > max(DISPLAY_TENORS):
            continue

        forward_rates = _calculate_forward_rates_for_tenor(tenor, rate, tenors, tenor_rates)
        tenor_rates_forward[str(tenor)] = forward_rates

    return _format_forward_rates(tenor_rates_forward)

def _calculate_forward_rates_for_tenor(tenor, rate, tenors, tenor_rates):
    forward_rates = {}

    for tenor2 in DISPLAY_TENORS:
        f_tenor = tenor + tenor2

        if tenor2 == 0:
            forward_rates[str(tenor2)] = rate
            continue
        elif f_tenor > max(DISPLAY_TENORS):
            continue

        smaller_tenor = max([t for t in tenors if t < f_tenor], default=min(tenors))
        bigger_tenor = min([t for t in tenors if t > f_tenor], default=max(tenors))

        if smaller_tenor != bigger_tenor:
            forward_rates[str(tenor2)] = _interpolate_forward_rate(
                tenor, rate, f_tenor, smaller_tenor, bigger_tenor, tenor_rates
            )

    return forward_rates

def _interpolate_forward_rate(tenor, rate, f_tenor, smaller_tenor, bigger_tenor, tenor_rates):
    smaller_rate = tenor_rates[smaller_tenor]
    bigger_rate = tenor_rates[bigger_tenor]

    interpolated_rate = smaller_rate + (
        (f_tenor - smaller_tenor) / (bigger_tenor - smaller_tenor)
        * (bigger_rate - smaller_rate)
    )

    return (interpolated_rate * f_tenor - rate * tenor) / (f_tenor - tenor)

def _format_forward_rates(tenor_rates_forward):
    grid_df = pd.DataFrame.from_dict(tenor_rates_forward, orient='index').reset_index()

    tenor_columns = [float(col) for col in grid_df.columns if col != 'index']
    tenor_dict = dict(zip(tenor_columns, convert_floats_to_tenor(tenor_columns)))
    tenor_dict['index'] = 'Forward \ Tenor'

    grid_df = grid_df.rename(columns=tenor_dict)
    grid_df['Forward \ Tenor'] = convert_floats_to_tenor(
        [float(tenor) for tenor in grid_df['Forward \\ Tenor']]
    )

    return grid_df