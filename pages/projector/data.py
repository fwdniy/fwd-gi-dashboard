import streamlit as st
from streamlit import session_state as ss
import pandas as pd

from .cashflow import build_cashflows, build_yearly_cashflow_df

@st.cache_data(show_spinner=False)
def get_liabilities(date):
    sql = f"SELECT group_name, year, value, mode FROM liability_profile.hk_liabilities WHERE as_of_date = (SELECT max(as_of_date) AS max_date FROM liability_profile.hk_liabilities WHERE as_of_date <= '{date}');"
    df = ss.snowflake.query(sql)
    
    return df

def verify_to_load():
    checks = [
        (len(ss.selected_groups) == 0, "Please select at least one fund.")
    ]

    load = False

    if st.button('Load Data'):
        load = True
        for condition, message in checks:
            if condition:
                st.warning(message)
                load = False

    if not load:
        st.stop()
        
def load_data(cashflow_types):
    date = ss.selected_date
    cf_df, pos_df = _get_asset_data(date)
    
    if len(pos_df) == 0:
        st.error('No data available for the selected fund.')
        st.stop()
    
    df = build_cashflows(pos_df, cf_df)
    
    df = _clean_positions(df)

    security_df, yearly_df = build_yearly_cashflow_df(df, cashflow_types)
    
    return security_df, yearly_df

def _get_asset_data(date):
    sql = f"SELECT bbgid, category, value FROM supp.cashflow_dates WHERE valuation_date = '{date}';"
    cf_df = ss['cashflow_df'] = ss.snowflake.query(sql)
    sql = f"SELECT closing_date, position_id, lbu_code, fund_code, fwd_asset_type, account_code, bbg_asset_type, security_name, bbgid_v2, isin, effective_maturity, maturity, next_call_date, coupon_rate, coupnfreq, position, unit, mtge_factor, principal_factor, redemption_value, next_call_price, currency, fx_rate, net_mv, time_until_maturity FROM funnel.funnelweb WHERE closing_date = '{date}' AND lbu_group = 'HK' AND is_bbg_fi = TRUE;"
    pos_df = ss['pos_df'] = ss.snowflake.query(sql)
    
    return cf_df, pos_df

def _clean_positions(df):
    
    filters = {
        'SECURITY_NAME': [],
        'BBG_ASSET_TYPE': ['Repo Liability', 'Bond Option'],
        'FWD_ASSET_TYPE': ['Listed Equity - Local', 'Listed Equity - International', 'Liability hedging assets']
    }

    for column, values in filters.items():
        df = df[~df[column].isin(values)]

    return df

def build_asset_liability_df(asset_df, cashflow_types):
    date = ss.selected_date
    groups = ss.selected_groups
    
    liab_df = get_liabilities(date)
    liab_df = liab_df[liab_df['GROUP_NAME'].isin(groups)]
    liab_df = liab_df[liab_df['MODE'].isin(ss.selected_options_labels)]
    liab_df = liab_df.groupby(['YEAR', 'MODE'], as_index=False)['VALUE'].sum()
    liab_df = liab_df.pivot(index='YEAR', columns='MODE', values='VALUE').reset_index()
    
    df = pd.merge(asset_df, liab_df, on='YEAR', how='outer')
    df = df[df['YEAR'] <= 50]
    
    df.fillna(0, inplace=True)
    
    df['Net Cashflow'] = df.drop(columns=['YEAR']).sum(axis=1)
    df['Cumulative Cashflow'] = df['Net Cashflow'].cumsum()
    
    return df