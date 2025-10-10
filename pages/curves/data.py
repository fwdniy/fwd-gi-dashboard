import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from utils.curve import convert_tenors_to_float

def build_spot_df(df):
    tenor_rate_dict = dict(zip(df['TENOR'], df['RATE']))
    tenor_dict = convert_tenors_to_float(tenor_rate_dict)
    tenors = list(tenor_dict.keys())
    rates = list(tenor_dict.values())
    date = df['VALUATION_DATE'].iloc[0]
    curve = df['CURVE'].iloc[0]
    
    values = pd.DataFrame({'CURVE': [curve] * len(tenors), 'VALUATION_DATE': [date] * len(tenors), 'TENOR': tenors,'RATE': rates})
    
    return values, tenors, rates