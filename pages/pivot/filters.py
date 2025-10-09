import streamlit as st
from streamlit import session_state as ss
from db.data.data_shipment import get_funnelweb_dates
from interface.filters import build_date_filter_pills, build_lbu_filter, build_multi_select_filter

def build_filters(config):
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
        
        build_multi_select_filter('Columns', config.COLUMNS, 'selected_columns')
        build_multi_select_filter('Values', config.VALUES, 'selected_values')
        