import streamlit as st
from streamlit import session_state as ss
import pandas as pd
from auth.authenticate import get_user_permissions
import json

# Get Positions
def get_data():
    selected_dates = ss.selected_dates
    
    df = _get_positions(selected_dates)
    
    df = _filter_data(df)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _get_positions(selected_dates):
    selected_dates_string = "', '".join([date.strftime('%Y-%m-%d') for date in selected_dates])
    
    sql = f"""SELECT closing_date, position_id, lbu_group, lbu_code, fund_code, manager, fwd_asset_type, bbg_asset_type, l1_asset_type, security_name, net_mv, first_acquired_date, is_ig, currency, fx_rate, bbgid_v2, ytm, developed_country, coll_typ   
            FROM funnel.funnelweb 
            WHERE closing_date IN ('{selected_dates_string}') 
            ORDER BY closing_date"""
            
    df = ss.snowflake.query(sql)
        
    return df

def _filter_data(df):
    # Make Macau a separate LBU
    macau_mask = df['FUND_CODE'].str.contains('Macau', na=False)
    df.loc[macau_mask, 'LBU_CODE'] = 'MC'
    
    # Consolidate Pinebridge
    pb_mask = df['MANAGER'].str.contains('Pinebridge', na=False)
    df.loc[pb_mask, 'MANAGER'] = 'Pinebridge'
    
    # Consolidate cash
    cash_mask = df['BBG_ASSET_TYPE'] == 'Cash'
    df.loc[cash_mask, 'FWD_ASSET_TYPE'] = 'Cash'
    
    # Apollo Treasury Msak
    apollo_cash_mask = (df['BBG_ASSET_TYPE'] == 'Treasury') & (df['MANAGER'] == 'Apollo')
    df.loc[apollo_cash_mask, 'FWD_ASSET_TYPE'] = 'Cash'
    non_corp_hga_asset_types = ['ASSET BACKED', 'MORTGAGE BACKED']
    apollo_hga_corp_mask = (df['FWD_ASSET_TYPE'] == 'Private Debt') & (df['BBG_ASSET_TYPE'] == 'Corporate Bond') & (~df['COLL_TYP'].isin(non_corp_hga_asset_types)) & (df['MANAGER'] == 'Apollo')
    apollo_dm_corp_mask = (df['DEVELOPED_COUNTRY'] == True) & (df['FWD_ASSET_TYPE'] == 'Corporate Bonds - Asia') & (df['MANAGER'] == 'Apollo')
    apollo_repo_mask = (df['BBG_ASSET_TYPE'] == 'Repo Liability') & (df['MANAGER'] == 'Apollo')
    apollo_gov_corp_mask = (df['BBG_ASSET_TYPE'] == 'Government Bond') & (df['MANAGER'] == 'Apollo')
    df.loc[apollo_hga_corp_mask | apollo_dm_corp_mask | apollo_repo_mask, 'FWD_ASSET_TYPE'] = 'Corporate Bonds - US'
    df.loc[apollo_gov_corp_mask, 'FWD_ASSET_TYPE'] = 'Corporate Bonds - Asia'
        
    # Negative cash
    neg_cash_mask = (df['BBG_ASSET_TYPE'] == 'Cash') & (df['NET_MV'] < 0.0)
    df.loc[neg_cash_mask, 'NET_MV'] = 0.0
    
    df['CLOSING_DATE'] = pd.to_datetime(df['CLOSING_DATE']).dt.date
    
    return df

# Get Fee Data
def get_fee_data(config):
    config.CALC_MODES, config.CALC_MODES_ID = _get_calc_modes()
    config.MV_MODES, config.MV_MODES_ID = _get_mv_modes()
    config.MANAGERS, config.MANAGERS_ID, config.MANAGERS_MV_MODES = _get_managers()
    config.USER_DICT, config.USER_DICT_ID = _get_users()
    config.FEE_GROUPS = _get_ima_fees()
    config.FEE_DETAILS = _get_ima_fees_details()
    config.CUSTOM_MANAGER_DATA = _get_custom_manager_data()
    
    return config

@st.cache_data(ttl=3600, show_spinner=False)
def _get_calc_modes():
    sql = 'SELECT id, mode FROM fees.calc_mode;'
    df = ss.snowflake.query(sql)
    mode_dict = dict(zip(df['ID'], df['MODE']))
    mode_id_dict = dict(zip(df['MODE'], df['ID']))
    
    return mode_dict, mode_id_dict

@st.cache_data(ttl=3600, show_spinner=False)
def _get_mv_modes():
    sql = 'SELECT id, mode FROM fees.mv_mode;'
    df = ss.snowflake.query(sql)
    mode_dict = dict(zip(df['ID'], df['MODE']))
    mode_id_dict = dict(zip(df['MODE'], df['ID']))
    
    return mode_dict, mode_id_dict

@st.cache_data(ttl=3600, show_spinner=False)
def _get_managers():
    sql = 'SELECT id, name, mv_mode_id FROM supp.manager_group;'
    df = ss.snowflake.query(sql)
    manager_dict = dict(zip(df['ID'], df['NAME']))
    manager_id_dict = dict(zip(df['NAME'], df['ID']))
    manager_mv_dict = dict(zip(df['ID'], df['MV_MODE_ID']))
    
    return manager_dict, manager_id_dict, manager_mv_dict

@st.cache_data(ttl=3600, show_spinner=False)
def _get_users():
    df = get_user_permissions()
    user_dict = dict(zip(df['ID'], df['EMAIL']))
    user_id_dict = dict(zip(df['EMAIL'], df['ID']))
    
    return user_dict, user_id_dict

@st.cache_data(ttl=3600, show_spinner=False)
def _get_ima_fees():
    sql = """
    WITH max_date AS (
        SELECT 
            lbu_code, 
            manager_id, 
            MAX(effective_date) AS max_eff_date 
        FROM 
            fees.ima_fees 
        GROUP BY 
            lbu_code, 
            manager_id
    )
    SELECT 
        id, 
        f.lbu_code, 
        f.manager_id, 
        asset_type, 
        effective_date, 
        created_at, 
        created_by_id 
    FROM 
        fees.ima_fees f
    JOIN 
        max_date m 
    ON 
        f.lbu_code = m.lbu_code 
        AND f.manager_id = m.manager_id 
        AND effective_date = max_eff_date;
    """
    df = ss.snowflake.query(sql)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _get_ima_fees_details():
    sql = 'SELECT id, fee_id, fee_bps, calc_mode_id, calc_mode_args, created_at, created_by_id FROM fees.ima_fees_bps;'
    df = ss.snowflake.query(sql)
    
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def _get_custom_manager_data():
    sql = 'SELECT manager_id, category, value, value2, created_at, created_by_id FROM fees.custom_fees;'
    df = ss.snowflake.query(sql)
    
    return df

def process_fee_data(config):
    df = config.FEE_GROUPS
    df['MANAGER'] = df['MANAGER_ID'].map(config.MANAGERS)
    df['MANAGER_MV_MODE_ID'] = df['MANAGER_ID'].map(config.MANAGERS_MV_MODES)
    df['MANAGER_MV_MODE'] = df['MANAGER_ID'].map(config.MANAGERS_MV_MODES).map(config.MV_MODES)
    df['CREATED_BY'] = df['CREATED_BY_ID'].map(config.USER_DICT)
    config.FEE_GROUPS = df
    
    df2 = config.FEE_DETAILS
    df2['CALC_MODE'] = df2['CALC_MODE_ID'].map(config.CALC_MODES)
    df2['CREATED_BY'] = df2['CREATED_BY_ID'].map(config.USER_DICT)
    df2['CALC_MODE_ARGS_DICT'] = df2['CALC_MODE_ARGS'].apply(lambda x: json.loads(x) if x else {})
    config.FEE_DETAILS = df2
    
    df2_highest = df2.loc[df2.groupby('FEE_ID')['ID'].idxmax()]
    df2_highest = df2_highest.rename({'CREATED_AT': 'CREATED_AT_FEE', 'CREATED_BY': 'CREATED_BY_FEE'}, axis=1)
    
    config.FEES = df.merge(df2_highest, left_on='ID', right_on='FEE_ID', how='left')
    
    df3 = config.CUSTOM_MANAGER_DATA
    df3['MANAGER'] = df3['MANAGER_ID'].map(config.MANAGERS)
    df3['CREATED_BY'] = df3['CREATED_BY_ID'].map(config.USER_DICT)
    config.CUSTOM_MANAGER_DATA = df3
    
    return config