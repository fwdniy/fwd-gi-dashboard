import streamlit as st
from streamlit import session_state as ss
from db.data.data_shipment import get_funnelweb_dates
from interface.filters import build_date_filter_pills, build_lbu_filter

def build_filters():
    with st.expander('Filters', True):
        dates = get_funnelweb_dates()
        build_date_filter_pills('Valuation Date', dates, key='selected_date')
        build_date_filter_pills('Comparison Date', dates, key='selected_comparison_date', comparison_date=ss['selected_date'])
        build_lbu_filter()