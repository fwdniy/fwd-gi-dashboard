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
        
        build_lbu_filter()
        
        #endregion
        
        #region Column / Value Filters
        
        _, selected_columns = build_multi_select_filter('Columns', config.FILTER_COLUMNS, 'selected_columns', ['LBU Group', 'FWD Asset Type'], True)
        _, selected_values = build_multi_select_filter('Values', config.FILTER_VALUES, 'selected_values', ['Notional', 'Net MV'], True)

        #endregion
        
        _build_transactions_mode_filter(config)
    
    return selected_columns, selected_values

def _build_transactions_mode_filter(config):
    st.pills('Transactions Mode', [key for key in config.FILTER_VALUES if config.FILTER_VALUES[key] in config.TRANSACTIONS_MODES], selection_mode='single', default=[key for key in config.FILTER_VALUES if config.FILTER_VALUES[key] == config.TRANSACTIONS_MODES[0]], key='selected_mode')
    ss['selected_mode_converted'] = config.FILTER_VALUES[ss['selected_mode']]