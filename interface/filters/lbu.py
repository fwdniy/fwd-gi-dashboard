import streamlit as st
from streamlit import session_state as ss
from db.data.data_shipment import get_lbu_data, get_lbu_data_hk
from interface.filters.tree import build_nested_dict, create_tree_nodes, build_tree_filter, _get_expanded_values
from db.data.lbu import LBU_GROUP, LBU_GROUP_NAME, LBU_CODE, LBU_CODE_NAME, FUND_TYPE, FUND_CODE, SUB_LBU, HK_CODE

def build_lbu_filter(funds = []):
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
    
    # Create tree nodes with label/value mapping
    nodes = create_tree_nodes(nested_dict, column_mapping, df)
    
    # Create "Select All" node at the top with all nodes as children
    all_node = {
        "label": "Select All",
        "value": "all",
        "children": nodes
    }
    
    
    # Get expanded values only for the Select All node
    expanded_values = _get_expanded_values([all_node], None)
    
    selected = build_tree_filter(
        "LBU Group / LBU Code / Fund Type / Fund Code", 
        [all_node], 
        "lbu_filter", 
        ["all"], 
        expanded_values, 
        300
    )
    
    selected_funds = [selection.replace(FUND_CODE + ':', "") for selection in selected['checked'] if FUND_CODE in selection]
    
    ss['selected_funds'] = selected_funds
    
def build_lbu_filter_hk(fund_codes = []):
    df = ss['lbu_df_hk'] = get_lbu_data_hk(SUB_LBU, HK_CODE, FUND_CODE)
    
    df = df[df[FUND_CODE].isin(fund_codes)] if fund_codes else df
        
    # Define the column mappings for labels and values
    column_mapping = [
        {'label': SUB_LBU, 'value': SUB_LBU},
        {'label': FUND_TYPE, 'value': FUND_TYPE},
        {'label': HK_CODE, 'value': HK_CODE}
    ]
    
    nested_dict = build_nested_dict(df, [mapping['value'] for mapping in column_mapping])
     
    # Create tree nodes with label/value mapping
    nodes = create_tree_nodes(nested_dict, column_mapping, df)
    
    # Create "Select All" node at the top with all nodes as children
    all_node = {
        "label": "Select All",
        "value": "all",
        "children": nodes
    }
    
    # Get expanded values only for the Select All node
    expanded_values = _get_expanded_values([all_node], None)
    
    selected = build_tree_filter(
        "HK Entity / Fund Type / HK Fund Code", 
        [all_node], 
        "lbu_filter_hk", 
        ["all"], 
        expanded_values, 
        300
    )
    
    mapping_dict = {f"{row[SUB_LBU]}:{row[HK_CODE]}": row[FUND_CODE] for _, row in df.iterrows()}
    
    selected_funds = [mapping_dict[selection.replace(HK_CODE + ':', '')] for selection in selected['checked'] if HK_CODE in selection]
    
    ss['selected_funds'] = selected_funds