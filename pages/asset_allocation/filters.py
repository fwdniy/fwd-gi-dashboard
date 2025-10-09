import streamlit as st
from streamlit import session_state as ss
from db.data.data_shipment import get_funnelweb_dates
from interface.filters import build_date_filter_pills, build_lbu_filter, build_fx_filter

def build_filters():
    with st.expander('Filters', True):
        #region Date Filters
        
        dates = get_funnelweb_dates()
        
        build_date_filter_pills('Valuation Date', dates, key='selected_date')
        ss.end_date = ss['selected_date']
        ss.end_date_string = ss['selected_date_string']
        
        build_date_filter_pills('Comparison Date', dates, key='selected_comparison_date', comparison_date=ss['selected_date'])
        ss.start_date = ss['selected_comparison_date']
        ss.start_date_string = ss['selected_comparison_date_string']
        
        #endregion
        
        build_lbu_filter()
        
        build_fx_filter()
        
        build_level_filter()
        
def build_level_filter():
    st.pills('Levels', ['1', '2', '3', '4'], selection_mode='single', default='2', key='selected_level')