import streamlit as st
from streamlit import session_state as ss
import pandas as pd

@st.cache_data(show_spinner=False)
def get_curves():
    sql = (
        "SELECT valuation_date, curve, fx, tenor, rate "
        "FROM supp.curve_rates r, supp.curve_name c "
        "WHERE valuation_date >= '2021-12-31' "
        "AND r.curve = c.name "
        "ORDER BY valuation_date, curve, tenor;"
    )

    df = ss.snowflake.query(sql)

    return df

@st.cache_data(show_spinner=False)
def convert_tenors_to_float(rates: dict[str, float]):
    tenor_mapping: dict[str, float] = {"1m": 1 / 12, "3m": 3 / 12, "6m": 6 / 12}
    rates_converted: dict[float, float] = {}

    for tenor, rate in rates.items():
        if tenor.isdigit():
            rates_converted[float(tenor)] = float(rate)
        elif tenor in tenor_mapping.keys():
            rates_converted[tenor_mapping[tenor]] = float(rate)
        else:
            print(f"Unknown tenor name '{tenor}'!")

    rates_converted = dict(sorted(rates_converted.items()))

    return rates_converted

@st.cache_data(show_spinner=False)
def convert_floats_to_tenor(tenors: list[float]):
    # Round tenor_mapping values to 6 decimal places
    tenor_mapping: dict[str, float] = {key: round(value, 6) for key, value in {"1m": 1 / 12, "3m": 3 / 12, "6m": 6 / 12}.items()}
    tenors_converted: list[str] = []

    for tenor in tenors:
        # Round tenor to 6 decimal places for comparison
        rounded_tenor = round(tenor, 6)
        
        if rounded_tenor in tenor_mapping.values():
            index = list(tenor_mapping.values()).index(rounded_tenor)
            tenors_converted.append(list(tenor_mapping.keys())[index])
        else:
            tenors_converted.append(f'{int(tenor)}y')

    return tenors_converted

def build_spot_df(df):
    tenor_rate_dict = dict(zip(df['TENOR'], df['RATE']))
    tenor_dict = convert_tenors_to_float(tenor_rate_dict)
    tenors = list(tenor_dict.keys())
    rates = list(tenor_dict.values())
    date = df['VALUATION_DATE'].iloc[0]
    curve = df['CURVE'].iloc[0]
    
    values = pd.DataFrame({'CURVE': [curve] * len(tenors), 'VALUATION_DATE': [date] * len(tenors), 'TENOR': tenors,'RATE': rates})
    
    return values, tenors, rates