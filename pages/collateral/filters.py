import streamlit as st
from streamlit import session_state as ss
from interface.filters import build_lbu_filter_hk, build_custom_tree_filter
from .data import get_csa_data
import pandas as pd
from db.data.lbu import FUND_TYPE, FUND_CODE

@st.fragment
def build_filters(config):
    with st.expander('Filters', True):
        config = get_csa_data(config)
        
        config = filter_corporate_bond_csas(config)
                
        build_counterparty_filter(config)
        
        build_asset_type_filter(config)
        
        build_custom_fund_filter(config.FUNDS)

def filter_corporate_bond_csas(config, selected_cps=None, selected_asset_types=None):
    csa_valuations = config.CSA_VALUATIONS
    csa_details = config.CSA_DETAILS
    csa_funds_mapped = config.CSA_FUNDS_MAPPED
    csa_logics = config.CSA_LOGICS
    
    corp_csa_ids = csa_valuations[csa_valuations['ASSET_TYPE'] == 'Corporate Bonds']['CSA_ID'].unique().tolist()
    corp_csa_details = csa_details[csa_details['ID'].isin(corp_csa_ids)]
    
    if selected_cps is not None:
        corp_csa_details = corp_csa_details[corp_csa_details['NAME'].isin(selected_cps)]
    
    corp_csa_ids = list(corp_csa_details['ID'])
    
    csa_valuations = csa_valuations[csa_valuations['CSA_ID'].isin(corp_csa_ids)]
    csa_funds_mapped = csa_funds_mapped[csa_funds_mapped['CSA_ID'].isin(corp_csa_ids)]
    csa_logics = csa_logics[csa_logics['CSA_ID'].isin(corp_csa_ids)]
    
    if selected_asset_types is not None:
        csa_valuations = csa_valuations[csa_valuations['ASSET_TYPE'].isin(selected_asset_types)]
            
    config.CSA_COUNTERPARTIES = corp_csa_details['NAME'].unique().tolist()
    config.CSA_FUNDS_MAPPED = csa_funds_mapped
    config.CSA_VALUATIONS = csa_valuations
    config.CSA_DETAILS = corp_csa_details
    config.CSA_LOGICS = csa_logics
    
    return config

def build_counterparty_filter(config):
    counterparties = config.CSA_COUNTERPARTIES
    st.multiselect('Counterparties', counterparties, default=counterparties, key='selected_cps')
    
    config = filter_corporate_bond_csas(config, selected_cps=ss.selected_cps)
    
    return config

def build_asset_type_filter(config):
    csa_valuations = config.CSA_VALUATIONS
    asset_types = csa_valuations['ASSET_TYPE'].unique().tolist()
    
    st.multiselect('Asset Types', asset_types, default=asset_types, key='selected_asset_types')

    config = filter_corporate_bond_csas(config, selected_asset_types=ss.selected_asset_types)

    return config

def build_custom_fund_filter(funds):
    df = pd.DataFrame(
        [(key, value) for key, values in funds.items() for value in values],
        columns=[FUND_TYPE, FUND_CODE ]
    )
    
    column_mapping = [
        {'label': FUND_TYPE, 'value': FUND_TYPE},
        {'label': FUND_CODE, 'value': FUND_CODE}
    ]
    
    
    selected = build_custom_tree_filter(
        'Fund Type / Fund Code*',
        'lbu_filter_custom',
        df,
        column_mapping,
        funds,
    )
        
    selected_funds = [selection.replace(FUND_CODE + ':', "") for selection in selected['checked'] if FUND_CODE in selection]
    
    ss['selected_funds'] = selected_funds
    
    st.caption('*The list of funds are overriden and limited by request of HK Investments as of Nov 2025.')