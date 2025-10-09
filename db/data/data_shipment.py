import streamlit as st
from streamlit import session_state as ss
from datetime import datetime
import pandas as pd

@st.cache_data(show_spinner=False)
def get_funnelweb_dates() -> list[datetime]:
    sql = 'SELECT DISTINCT closing_date FROM funnelweb WHERE closing_date >= \'2021-12-31\' ORDER BY closing_date;'
    df = ss.snowflake.query(sql)
    
    dates = df['CLOSING_DATE'].unique()
    
    return dates

@st.cache_data(show_spinner=False)
def get_lbu_data():
    sql = "SELECT l.group_name, f.lbu, f.type, f.short_name, l.bloomberg_name, l.lbu_group, f.sub_lbu, f.vfa, f.hk_code FROM supp.fund AS f LEFT JOIN supp.lbu AS l ON l.name = f.lbu WHERE l.bloomberg_name <> \'LT\' AND f.type <> 'N/A' ORDER BY group_name, lbu, sub_lbu, type, short_name;"
    df = ss.snowflake.query(sql)
    
    return df

@st.cache_data(show_spinner=False)
def get_lbu_data_hk(SUB_LBU, HK_CODE, FUND_CODE):
    df = get_lbu_data()
    
    df = df[df[SUB_LBU] != 'None']
    missing_df = df[df[HK_CODE] == 'None']
    
    if len(missing_df) > 0:
        st.warning(f"The following funds is not mapped to a three letter HK code: {', '.join(missing_df[FUND_CODE].tolist())}! Please contact {st.secrets['admin']['name']}.")
        df = df[df[HK_CODE] != 'None']
        
    return df

@st.cache_data(show_spinner=False)
def get_fx_data():
    """Get all FX data (consider using more specific functions above instead)"""
    sql: str = 'SELECT valuation_date, fx, rate FROM supp.fx_rates WHERE valuation_date >= \'2021-12-31\' ORDER BY valuation_date, fx;'
    df = ss.snowflake.query(sql)
    
    df['VALUATION_DATE'] = pd.to_datetime(df['VALUATION_DATE']).dt.date
    
    return df