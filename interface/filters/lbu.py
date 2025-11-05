import streamlit as st
from streamlit import session_state as ss
from db.data.data_shipment import get_lbu_data, get_lbu_data_hk
from interface.filters.tree import build_nested_dict, build_custom_tree_filter
from db.data.lbu import LBU_GROUP, LBU_GROUP_NAME, LBU_CODE, LBU_CODE_NAME, FUND_TYPE, FUND_CODE, SUB_LBU, HK_CODE

def build_lbu_filter():
    df = get_lbu_data()
    
    lbu = ss['lbu']
    
    if lbu != 'Group':
        df = df[df[LBU_GROUP] == lbu]
    
    # Define the column mappings for labels and values
    column_mapping = [
        {'label': LBU_GROUP_NAME, 'value': LBU_GROUP},
        {'label': LBU_CODE_NAME, 'value': LBU_CODE},
        {'label': FUND_TYPE, 'value': FUND_TYPE},
        {'label': FUND_CODE, 'value': FUND_CODE}
    ]
    
    nested_dict = build_nested_dict(df, [mapping['value'] for mapping in column_mapping])
    
    selected = build_custom_tree_filter(
        'LBU Group / LBU Code / Fund Type / Fund Code', 
        'lbu_filter',
        df,
        column_mapping,
        nested_dict
    )
    
    selected_funds = [selection.replace(FUND_CODE + ':', "") for selection in selected['checked'] if FUND_CODE in selection]
    
    ss['selected_funds'] = selected_funds
    
def build_lbu_filter_hk(fund_codes = []):
    df = get_lbu_data_hk()
    
    df = df[df[FUND_CODE].isin(fund_codes)] if fund_codes else df
        
    # Define the column mappings for labels and values
    column_mapping = [
        {'label': SUB_LBU, 'value': SUB_LBU},
        {'label': FUND_TYPE, 'value': FUND_TYPE},
        {'label': HK_CODE, 'value': HK_CODE}
    ]
    
    nested_dict = build_nested_dict(df, [mapping['value'] for mapping in column_mapping])
     
    expanded_level = None
    if fund_codes:
        expanded_level = LBU_GROUP
        
    selected = build_custom_tree_filter(
        'HK Entity / Fund Type / HK Fund Code', 
        'lbu_filter_hk',
        df,
        column_mapping,
        nested_dict,
        expanded_level=expanded_level
    )
    
    mapping_dict = {f"{row[SUB_LBU]}:{row[HK_CODE]}": row[FUND_CODE] for _, row in df.iterrows()}
    
    selected_funds = [mapping_dict[selection.replace(HK_CODE + ':', '')] for selection in selected['checked'] if HK_CODE in selection]
    
    ss['selected_funds'] = selected_funds