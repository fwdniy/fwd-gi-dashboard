import streamlit as st
from interface import initialize
from pages.projector import build_filters, verify_to_load, load_data, build_asset_liability_df, build_visuals

CASHFLOW_TYPES = {'asset': 'Asset Cashflows', 'prem_cf': 'Premiums', 'g_liab': 'Guaranteed Liabilities', 'ng_liab': 'Non-Guaranteed Liabilities'}
CASHFLOW_COLORS = {'asset': '#F3BB90', 'prem_cf': '#B5E6A2', 'g_liab': '#EDEFF0', 'ng_liab': '#F2CEEF'}

initialize()

build_filters(CASHFLOW_TYPES)

verify_to_load()

security_df, yearly_df = load_data(CASHFLOW_TYPES)

yearly_df = build_asset_liability_df(yearly_df, CASHFLOW_TYPES)
    
build_visuals(yearly_df, CASHFLOW_TYPES, CASHFLOW_COLORS, security_df)