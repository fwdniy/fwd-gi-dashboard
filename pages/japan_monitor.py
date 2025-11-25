import streamlit as st
from interface import initialize
from pages.japan_monitor import get_policy_data, build_aum_cards, get_funnelweb_metrics, build_yield_cards, build_profile_grid, build_yield_grid, build_cashflow_df, initialize_settings, build_duration_grid
from pages.projector import load_asset_cashflow_data, build_visuals

CASHFLOW_TYPES = {'asset': 'Asset Cashflows', 'g_liab': 'Guaranteed Liabilities'}
CASHFLOW_COLORS = {'asset': '#F3BB90', 'g_liab': '#A9A9A9'}

initialize()
  
initialize_settings(CASHFLOW_TYPES)  

security_df, cashflow_df = load_asset_cashflow_data(CASHFLOW_TYPES, ['CAYMAN_MRE'], True)

pol_df = get_policy_data()
aum_df = get_funnelweb_metrics()

build_aum_cards(pol_df, aum_df)

build_yield_cards()

build_profile_grid(pol_df, aum_df)

build_yield_grid(pol_df, aum_df)

period_df = build_cashflow_df(cashflow_df, pol_df)

build_visuals(period_df, CASHFLOW_TYPES, CASHFLOW_COLORS, security_df, True, True)

build_duration_grid(pol_df, aum_df)