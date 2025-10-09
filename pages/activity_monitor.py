import streamlit as st
from streamlit import session_state as ss
from interface import initialize
from utils.initializer import initialize_variables
from pages.activity_monitor import build_filters, verify_to_load, get_data, compute_transactions, build_value_columns, build_grid_and_analysis

initialize()

class ActivityMonitorConfig:
    #region Filter fields
    FILTER_COLUMNS = {
        'LBU Group': 'LBU_GROUP', 
        'Fund Code': 'FUND_CODE', 
        'Account Code': 'ACCOUNT_CODE', 
        'Final Rating': 'FINAL_RATING', 
        'Final Rating Letter': 'FINAL_RATING_LETTER', 
        'Country': 'COUNTRY_REPORT', 
        'Manager': 'MANAGER', 
        'Maturity Range': 'MATURITY_RANGE', 
        'FWD Asset Type': 'FWD_ASSET_TYPE', 
        'L1 Asset Type': 'L1_ASSET_TYPE', 
        'L2 Asset Type': 'L2_ASSET_TYPE', 
        'L3 Asset Type': 'L3_ASSET_TYPE', 
        'BBG Asset Type': 'BBG_ASSET_TYPE', 
        'Currency': 'CURRENCY', 
        'Security Name': 'SECURITY_NAME'
    }
    
    FILTER_VALUES = {
        'Net MV': 'NET_MV', 
        'Notional': 'NOTIONAL_USD', 
        'Duration': 'DURATION', 
        'WARF': 'WARF',
        'Credit Spread': 'CREDIT_SPREAD_BP',
    }
    
    FILTER_VALUES_SUM = {
        'NET_MV': 1_000_000, 
        'NOTIONAL_USD': 1_000_000
    }
    
    FILTER_VALUES_WA = ['DURATION', 'WARF']
    
    TRANSACTIONS_MODES = ['NET_MV', 'NOTIONAL_USD']
    
    #endregion
    
    #region Query Fields
    
    IDENTIFIER_COLUMNS = ['closing_date', 'position_id', 'security_name', 
                          'bbgid_v2', 'lbu_group', 'lbu_code', 
                          'fund_code', 'account_code']
    
    STATIC_COLUMNS = ['country_report', 'manager', 'fwd_asset_type', 
                      'l1_asset_type', 'l2_asset_type', 'l3_asset_type', 
                      'bbg_asset_type', 'currency', 'maturity', 
                      'securitized_credit_type', 'sw_rec_crncy', 
                      'underlying_security_name', 'issuer', 'fund_geo_focus']
    
    CHARACTERISTIC_COLUMNS = ['net_mv', 'duration', 'final_rating', 
                              'final_rating_letter', 'maturity_range', 'mtge_factor', 
                              'principal_factor', 'last_trade_date', 'position', 
                              'unit', 'rate', 'warf', 'credit_spread_bp']
    
    FORMULA_COLUMNS = {
        'currency_pair': 'IFF(sw_pay_crncy IS NULL OR sw_rec_crncy IS NULL, NULL, sw_pay_crncy || \'/\' || sw_rec_crncy)'
    }
        
    #endregion
    
    INITIALIZE_DATA = {
        'previous_start_date': None,
        'previous_end_date': None,
        'previous_selected_columns': [],
        'previous_selected_values': [],
        'previous_selected_funds': [],
    }

initialize_variables(ActivityMonitorConfig.INITIALIZE_DATA)
selected_columns, selected_values = build_filters(ActivityMonitorConfig)
verify_to_load()

bar = st.progress(0, text="Getting data...")

df = get_data(ActivityMonitorConfig, bar)

df, trans_cols, trans_col_headers = compute_transactions(df)

value_columns = build_value_columns(ActivityMonitorConfig, df, selected_values)

build_grid_and_analysis(ActivityMonitorConfig, df, selected_columns, value_columns, trans_cols, trans_col_headers)

bar.progress(100)
bar.empty()