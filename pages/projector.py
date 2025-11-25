import streamlit as st
from interface import initialize
from pages.projector import build_filters, verify_to_load, load_asset_cashflow_data, build_asset_liability_df, build_visuals, get_liabilities

LBUS = ['HK', 'TH', 'JP']

initialize()

build_filters(CASHFLOW_TYPES)

verify_to_load()

security_df, yearly_df = load_asset_cashflow_data(CASHFLOW_TYPES, LBUS)

yearly_df = build_asset_liability_df(yearly_df, get_liabilities())

yearly_df = build_asset_liability_df(yearly_df)
    
build_visuals(yearly_df, CASHFLOW_TYPES, CASHFLOW_COLORS, security_df)