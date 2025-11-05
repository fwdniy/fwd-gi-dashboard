import streamlit as st
from streamlit import session_state as ss
from db.data.data_shipment import get_funnelweb_dates
from interface.filters import build_date_filter_pills
from .data import get_liabilities

@st.fragment
def build_filters(cashflow_types):
    with st.expander('Filters', True):
        dates = get_funnelweb_dates()
        
        build_date_filter_pills('Asset Date', dates, key='selected_date')        
        build_date_filter_pills('Liability Date', dates, key='selected_comparison_date', comparison_date=ss['selected_date'])
        
        build_liability_group_filters()
        _build_cashflow_types_filter(cashflow_types)
        
        st.number_input('Reinvestment Spread', value=100.0, key='reinvestment_spread', format='%f')
        
        st.checkbox('To Next Call Date Only', value=False, key='to_next_call_date')
        
def build_liability_group_filters():
    date = ss.selected_date
    df = get_liabilities(date)

    groups = list(df['GROUP_NAME'].unique())
    
    if len(groups) == 0:
        st.error('No liabilities found for provided date')
        st.run()

    selected_groups = st.segmented_control('Liability Groups', groups, default=groups[0], key='selected_groups', selection_mode='multi')

    ss.selected_funds = _get_funds(selected_groups)

def _get_funds(selected_groups):
    mapping = _get_fund_mapping()

    funds = [short_name for group in selected_groups for short_name in mapping[group]]

    return funds

@st.cache_data(ttl=3600, show_spinner=False)
def _get_fund_mapping():
    sql = 'SELECT cashflow_name, short_name FROM supp.fund WHERE cashflow_name IS NOT NULL ORDER BY cashflow_name'
    df = ss.snowflake.query(sql)

    mapping = df.groupby('CASHFLOW_NAME')['SHORT_NAME'].apply(list).to_dict()

    return mapping

def _build_cashflow_types_filter(cashflow_types):
    default_values = ['asset', 'g_liab', 'reinv']

    # Dynamically find the labels corresponding to the default values
    default_labels = sorted([cashflow_types[value] for value in default_values])

    selected_options_labels = st.segmented_control(
        'Cashflow Options',
        sorted(cashflow_types.values()),
        default=default_labels,  # Use the dynamically found labels
        key='selected_options_labels',
        selection_mode='multi'
    )

    # Map the selected labels back to their corresponding keys
    ss.selected_options = [key for key, value in cashflow_types.items() if value in selected_options_labels]