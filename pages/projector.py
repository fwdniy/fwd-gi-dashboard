import streamlit as st
from interface import initialize
from pages.projector import build_filters, verify_to_load, load_asset_cashflow_data, build_asset_liability_df, build_visuals, get_liabilities, calculate_reinvestment_rates

LBUS = ['HK', 'TH', 'JP']
CASHFLOW_TYPES = {'asset': 'Asset Cashflows', 'prem_cf': 'Premiums', 'g_liab': 'Guaranteed Liabilities', 'ng_liab': 'Non-Guaranteed Liabilities', 'reinv': 'Reinvestment Income', 'net_liab': 'Net Liabilities'}
CASHFLOW_COLORS = {'asset': '#F3BB90', 'prem_cf': '#B5E6A2', 'g_liab': '#A9A9A9', 'ng_liab': '#F2CEEF', 'reinv': '#A2D2E6', 'net_liab': '#D9A7A7'}

initialize()

build_filters(CASHFLOW_TYPES)

verify_to_load()

security_df, yearly_df = load_asset_cashflow_data(CASHFLOW_TYPES, LBUS)

yearly_df = build_asset_liability_df(yearly_df, get_liabilities())

calculate_reinvestment_rates(yearly_df, CASHFLOW_TYPES)
    
build_visuals(yearly_df, CASHFLOW_TYPES, CASHFLOW_COLORS, security_df)