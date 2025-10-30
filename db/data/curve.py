import streamlit as st
from streamlit import session_state as ss
from datetime import datetime
import pandas as pd

@st.cache_data(ttl=3600, show_spinner=False)
def get_curves():
    sql = (
        "SELECT valuation_date, curve, fx, tenor, rate "
        "FROM supp.curve_rates r, supp.curve_name c "
        "WHERE valuation_date >= '2021-12-31' "
        "AND r.curve = c.name "
        "ORDER BY valuation_date, curve, tenor;"
    )

    df = ss.snowflake.query(sql)
    
    df['VALUATION_DATE'] = pd.to_datetime(df['VALUATION_DATE']).dt.date

    return df

def get_curve(curve_name, valuation_date):
    if isinstance(valuation_date, (datetime, pd.Timestamp)):
        valuation_date = valuation_date.date()
    
    df = get_curves()
    df = df[(df['CURVE'] == curve_name) & (df['VALUATION_DATE'] == valuation_date)]
    
    return df