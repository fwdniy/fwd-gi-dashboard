import streamlit as st
from interface import initialize
from pages.collateral import build_filters, verify_to_load, get_data, calculate_haircuts, build_grid

class CollateralCalculatorConfig:
    REPORT_FIELDS = [
        'POSITION_ID',
        'FUND_CODE',
        'ACCOUNT_CODE',
        'SECURITY_NAME',
        'BBGID_V2',
        'ISIN',
        'NET_MV',
        'PLEDGE_POS',
    ]
    
    EXTRA_FIELDS = ['POSITION',
        'UNIT',
        'ISSUER',
    ]
    
    ELIGIBLE_ASSET_TYPES = {'Cash': 'Cash', 'JGB': 'Government Bond', 'UST': 'Treasury', 'HKGB': 'Government Bond', 'Corporate Bonds': 'Corporate Bond'}
    CUSTOM_FUNCTIONS = {}
    
    AGENCIES = {'S&P': 'SP', 'Moodys': 'MOODYS', 'Fitch': 'FITCH'}
    AGENCY_MAPPINGS = None
    
    CSA_FUNDS_MAPPED = None
    CSA_DETAILS = None
    CSA_LOGICS = None
    CSA_VALUATIONS = None
    CSA_COUNTERPARTIES = None

initialize()

build_filters(CollateralCalculatorConfig)

verify_to_load()

config, df = get_data(CollateralCalculatorConfig)

df = calculate_haircuts(config, df)

build_grid(config, df)