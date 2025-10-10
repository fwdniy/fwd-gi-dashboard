from .data import build_spot_df
import pandas as pd
from utils.curve import calculate_forward_rates_for_tenor, convert_floats_to_tenor

DISPLAY_TENORS = [0, 0.25, 0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20, 25, 30]

def calculate_forward_rates(df):
    _, tenors, rates = build_spot_df(df)
    tenor_rates = dict(zip(tenors, rates))
    tenor_rates_forward = {}

    for tenor, rate in tenor_rates.items():
        if tenor == 0 or tenor > max(DISPLAY_TENORS):
            continue

        forward_rates = calculate_forward_rates_for_tenor(tenor, rate, tenors, tenor_rates, DISPLAY_TENORS)
        tenor_rates_forward[str(tenor)] = forward_rates
        
    return tenor_rates_forward

def format_forward_rates(tenor_rates_forward):
    grid_df = pd.DataFrame.from_dict(tenor_rates_forward, orient='index').reset_index()

    tenor_columns = [float(col) for col in grid_df.columns if col != 'index']
    tenor_dict = dict(zip(tenor_columns, convert_floats_to_tenor(tenor_columns)))
    tenor_dict['index'] = 'Forward \ Tenor'

    grid_df = grid_df.rename(columns=tenor_dict)
    grid_df['Forward \ Tenor'] = convert_floats_to_tenor(
        [float(tenor) for tenor in grid_df['Forward \\ Tenor']]
    )

    return grid_df