import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from db.data.data_shipment import get_lbu_data
from db.data.data_shipment import get_funnelweb_dates

@st.cache_data(ttl=3600, show_spinner=False)
def get_policy_data():
    sql = """
        SELECT DISTINCT valuation_date FROM liability_profile.policy_jspa_ga ORDER BY valuation_date DESC;
    """
    
    df = ss.snowflake.query(sql)
    
    df['VALUATION_DATE'] = pd.to_datetime(df['VALUATION_DATE'])
    last_month_end = df['VALUATION_DATE'].max() - pd.offsets.MonthEnd(1)
    
    sql = f"""
        WITH max_date AS (
            SELECT policy_id, MAX(valuation_date) AS max_date
            FROM liability_profile.policy_jspa_ga
            GROUP BY policy_id
        )
        SELECT p.*
        FROM liability_profile.policy_jspa_ga p, max_date m
        WHERE valuation_date = m.max_date AND p.policy_id = m.policy_id AND max_date >= '{last_month_end.strftime('%Y-%m-%d')}';
    """
    df = ss.snowflake.query(sql)
    
    return df

def initialize_settings(cashflow_types):
    ss.selected_date = ss.selected_comparison_date = get_funnelweb_dates().max().date()

    ss.selected_funds = get_fund_names()
    
    ss.selected_groups = ['JSPA']
    
    ss.selected_options_labels = list(cashflow_types.values())

@st.cache_data(ttl=3600, show_spinner=False)
def get_fund_names():
    lbus_df = get_lbu_data()
    
    funds = lbus_df[lbus_df['SHORT_NAME'].str.contains('SPA ')]['SHORT_NAME'].tolist()
    
    return funds

@st.cache_data(ttl=3600, show_spinner=False)
def get_funnelweb_metrics():
    funds = get_fund_names()
    fund_string = "', '".join(funds)
    
    sql = f"""
        SELECT 
            closing_date, 
            fund_code, 
            SUM(net_mv) AS net_mv, 
            SUM(ytm * net_mv) / SUM(net_mv) AS weighted_avg_ytm,
            SUM(duration * net_mv) / SUM(net_mv) AS weighted_avg_duration
        FROM 
            funnel.funnelweb 
        WHERE 
            fund_code IN ('{fund_string}') 
        GROUP BY 
            closing_date, fund_code 
        ORDER BY 
            closing_date, fund_code;
    """
    
    df = ss.snowflake.query(sql)
    
    df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.date
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def get_yields(date):
    date = ss.selected_date
    
    sql = f"""
        SELECT 
            tenor, 
            rate 
        FROM 
            supp.curve_rates 
        WHERE 
            valuation_date = '{date.strftime('%Y-%m-%d')}' 
            AND curve = 'USD_govt' 
            AND tenor IN ('10', '15', '20');
    """
    
    ust_df = ss.snowflake.query(sql)
    
    sql = f"""
        SELECT 
            '10' AS tenor, 
            spread_bid 
        FROM 
            supp.cds_rates 
        WHERE 
            valuation_date = '{date.strftime('%Y-%m-%d')}' 
            AND name = 'CDX IG CDSI GEN 10Y Corp';
    """
    
    cds_df = ss.snowflake.query(sql)
    
    return ust_df, cds_df