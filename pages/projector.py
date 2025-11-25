import streamlit as st
from interface import initialize
from pages.projector import build_filters, verify_to_load, load_asset_cashflow_data, build_asset_liability_df, build_visuals, get_liabilities

LBUS = ['HK', 'TH', 'JP']
CASHFLOW_TYPES = {'asset': 'Asset Cashflows', 'prem_cf': 'Premiums', 'g_liab': 'Guaranteed Liabilities', 'ng_liab': 'Non-Guaranteed Liabilities', 'net_liab': 'Net Liabilities'}

initialize()

build_filters(CASHFLOW_TYPES)

verify_to_load()

security_df, yearly_df = load_asset_cashflow_data(CASHFLOW_TYPES, LBUS)

yearly_df = build_asset_liability_df(yearly_df, get_liabilities())

yearly_df = build_asset_liability_df(yearly_df)
    
build_visuals(yearly_df, CASHFLOW_TYPES, CASHFLOW_COLORS, security_df)