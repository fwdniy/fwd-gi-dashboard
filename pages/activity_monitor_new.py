import streamlit as st
from streamlit import session_state as ss
import pandas as pd

from utils.interface.menu import menu
from utils.initialize import initialize_variables

menu('pages/activity_monitor_new.py')

FILTER_COLUMNS = {'LBU Group': 'LBU_GROUP', 'Fund Code': 'FUND_CODE', 'Account Code': 'ACCOUNT_CODE', 'Final Rating': 'FINAL_RATING', 'Final Rating Letter': 'FINAL_RATING_LETTER', 'Country': 'COUNTRY_REPORT', 'Manager': 'MANAGER', 'Maturity Range': 'MATURITY_RANGE', 'FWD Asset Type': 'FWD_ASSET_TYPE', 'L1 Asset Type': 'L1_ASSET_TYPE', 'L2 Asset Type': 'L2_ASSET_TYPE', 'L3 Asset Type': 'L3_ASSET_TYPE', 'BBG Asset Type': 'BBG_ASSET_TYPE', 'Currency': 'CURRENCY', 'Security Name': 'SECURITY_NAME'}
FILTER_VALUES = {'Net MV': 'NET_MV', 'Notional': 'NOTIONAL_USD', 'Duration': 'DURATION', 'WARF': 'WARF'}
FILTER_VALUES_SUM = {'NET_MV': 1000000, 'NOTIONAL_USD': 1000000}
FILTER_VALUES_WA = ['DURATION', 'WARF']
TRANSACTIONS_MODES = ['NET_MV', 'NOTIONAL_USD']

IDENTIFIER_COLUMNS = ['closing_date', 'position_id', 'security_name', 'bbgid_v2', 'lbu_group', 'lbu_code', 'fund_code', 'account_code']
STATIC_COLUMNS = ['country_report', 'manager', 'fwd_asset_type', 'l1_asset_type', 'l2_asset_type', 'l3_asset_type', 'bbg_asset_type', 'currency', 'maturity', 'securitized_credit_type', 'sw_rec_crncy']
CHARACTERISTIC_COLUMNS = ['net_mv', 'duration', 'final_rating', 'final_rating_letter', 'maturity_range', 'mtge_factor', 'principal_factor', 'last_trade_date', 'position', 'unit', 'rate', 'warf']
FORMULA_COLUMNS = {'currency_pair': 'IFF(sw_pay_crncy IS NULL OR sw_rec_crncy IS NULL, NULL, sw_pay_crncy || \'/\' || sw_rec_crncy)'}