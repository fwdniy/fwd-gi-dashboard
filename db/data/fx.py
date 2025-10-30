import streamlit as st
from streamlit import session_state as ss
from datetime import datetime
import pandas as pd

from .data_shipment import get_fx_data

@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_list() -> list[str]:
    """Get a list of unique FX currencies"""
    df = get_fx_data()
    return sorted(df['FX'].unique())

@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rates_for_date(valuation_date: datetime) -> dict[str, float]:
    """Get all FX rates for a specific date
    
    Args:
        valuation_date (datetime): The date to get rates for
        
    Returns:
        dict[str, float]: Dictionary mapping currency codes to their rates
    """
    if isinstance(valuation_date, (datetime, pd.Timestamp)):
        valuation_date = valuation_date.date()
    
    df = get_fx_data()
    date_df = df[df['VALUATION_DATE'] == valuation_date]
    return dict(zip(date_df['FX'], date_df['RATE']))

#@st.cache_data(ttl=3600, show_spinner=False)
def get_fx_rate(fx: str, valuation_date: datetime) -> float:
    """Get a specific FX rate for a date
    
    Args:
        fx (str): The currency code
        valuation_date (datetime): The date to get the rate for
        
    Returns:
        float: The exchange rate
    """
    if isinstance(valuation_date, (datetime, pd.Timestamp)):
        valuation_date = valuation_date.date()
    
    df = get_fx_data()
    rate = df[(df['FX'] == fx) & (df['VALUATION_DATE'] == valuation_date)]['RATE']
    return float(rate.iloc[0]) if not rate.empty else None