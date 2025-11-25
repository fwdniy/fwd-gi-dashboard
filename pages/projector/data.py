import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from .cashflow import build_cashflows, build_cashflow_df
from db.data.fx import get_fx_rate

@st.cache_data(ttl=3600, show_spinner=False)
def get_liabilities():
    date = ss.selected_date
    
    hk_df = get_hk_liabilities(date)
    th_df = get_th_liabilities(date)
    jp_df = get_jp_liabilities(date)

    df = pd.concat([hk_df, th_df, jp_df], ignore_index=True)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def get_hk_liabilities(date):
    sql = f"SELECT group_name, year, value, mode FROM liability_profile.hk_liabilities WHERE as_of_date = (SELECT max(as_of_date) AS max_date FROM liability_profile.hk_liabilities WHERE as_of_date <= '{date}');"
    df = ss.snowflake.query(sql)
    
    if ss.lbu == 'HK' or ss.lbu == 'Group':
        return df
    else:
        return df.iloc[0:0]

@st.cache_data(ttl=3600, show_spinner=False)
def get_th_liabilities(date):
    sql = f"SELECT group_name, year, value, mode FROM liability_profile.th_liabilities_new WHERE as_of_date = (SELECT max(as_of_date) AS max_date FROM liability_profile.th_liabilities_new WHERE as_of_date <= '{date}');"
    df = ss.snowflake.query(sql)
    
    thb_fx = get_fx_rate('THB', date)
    df['VALUE'] = df['VALUE'] / thb_fx
    
    if ss.lbu == 'TH' or ss.lbu == 'Group':
        return df
    else:
        return df.iloc[0:0]

@st.cache_data(ttl=3600, show_spinner=False)
def get_jp_liabilities(date):
    sql = f"SELECT group_name, year, value, mode FROM liability_profile.jp_liabilities WHERE as_of_date = (SELECT max(as_of_date) AS max_date FROM liability_profile.jp_liabilities WHERE as_of_date <= '{date}');"
    df = ss.snowflake.query(sql)
    
    jpy_fx = get_fx_rate('JPY', date)
    df['VALUE'] = df['VALUE'] / jpy_fx
    
    if ss.lbu == 'JP' or ss.lbu == 'Group':
        return df
    else:
        return df.iloc[0:0]
    
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
        
def load_asset_cashflow_data(cashflow_types, lbus, monthly=False):
    date = ss.selected_date
    cf_df, pos_df = _get_asset_data(date, lbus)
    
    if len(pos_df) == 0:
        st.error('No data available for the selected fund.')
        st.stop()
    
    df = build_cashflows(pos_df, cf_df)
    
    df = _clean_positions(df)

    security_df, cashflow_df = build_cashflow_df(df, cashflow_types, monthly)
    
    return security_df, cashflow_df

@st.cache_data(ttl=3600, show_spinner=False)
def _get_asset_data(date, lbus):
    sql = f"SELECT bbgid, category, value FROM supp.cashflow_dates WHERE valuation_date = '{date}';"
    cf_df = ss['cashflow_df'] = ss.snowflake.query(sql)
    
    lbu_string = "', '".join(lbus)
    sql = f"SELECT closing_date, position_id, lbu_code, fund_code, manager, fwd_asset_type, account_code, bbg_asset_type, security_name, bbgid_v2, isin, effective_maturity, maturity, next_call_date, coupon_rate, coupnfreq, position, unit, mtge_factor, principal_factor, redemption_value, next_call_price, currency, fx_rate, net_mv, time_until_maturity FROM funnel.funnelweb WHERE closing_date = '{date}' AND lbu_group IN ('{lbu_string}') AND is_bbg_fi = TRUE;"
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

def build_asset_liability_df(asset_df, liab_df, monthly=False):
    period = 'YEAR'
    max_period = 50
    
    if monthly:
        period = 'MONTH'
        max_period *= 12
        
    groups = ss.selected_groups
    
    liab_df = liab_df[liab_df['GROUP_NAME'].isin(groups)]
    liab_df = liab_df[liab_df['MODE'].isin(ss.selected_options_labels)]
    liab_df = liab_df.groupby([period, 'MODE'], as_index=False)['VALUE'].sum()
    liab_df = liab_df.pivot(index=period, columns='MODE', values='VALUE').reset_index()
    
    asset_df = asset_df.rename(columns={'PERIOD': period})
    
    df = pd.merge(asset_df, liab_df, on=period, how='outer')
        
    df = df[df[period] <= max_period]
    
    df.fillna(0, inplace=True)
    
    df['Net Cashflow'] = df.drop(columns=[period, 'PRINCIPAL', 'COUPON']).sum(axis=1)
    df['Cumulative Cashflow'] = df['Net Cashflow'].cumsum()
    
    return df