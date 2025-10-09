import streamlit as st
from streamlit import session_state as ss
from streamlit_tree_select import tree_select
from collections import defaultdict

# Constants for column names
FUND_TYPE = 'TYPE'
LBU_CODE = 'BLOOMBERG_NAME'
LBU_GROUP = 'LBU_GROUP'
HK_CODE = 'HK_CODE'

def _collect_all_values(nodes):
    """
    Recursively collect all values from a tree structure.
    
    Parameters:
        nodes (list[dict]): List of tree nodes with optional 'children' key
        
    Returns:
        list: List of all values from the tree
    """
    values = []
    for node in nodes:
        values.append(node['value'])
        if 'children' in node:
            values.extend(_collect_all_values(node['children']))
    return values

def _get_expanded_values(nodes, expand_to_column, current_level=None):
    """
    Get list of values to expand up to a specific column level
    
    Parameters:
        nodes (list[dict]): List of tree nodes
        expand_to_column (str): Column name to expand to (e.g., 'LBU_CODE')
        current_level (str): Current column level being processed
        
    Returns:
        list: List of values to be expanded
    """
    expanded = []
    column_order = [None, LBU_GROUP, LBU_CODE, FUND_TYPE]  # None for 'all' node
    
    for node in nodes:
        value = node['value']
        expanded.append(value)
        
        # Determine current level from value
        if value == 'all':
            current_col = None
        elif ':' in value:
            current_col = value.split(':')[0]
        else:
            current_col = None
            
        # Get indices for current and target levels
        current_idx = column_order.index(current_col)
        target_idx = column_order.index(expand_to_column)
        
        # Only expand children if we haven't reached the target level yet
        if 'children' in node and current_idx < target_idx:
            expanded.extend(_get_expanded_values(node['children'], expand_to_column, current_col))
    
    return expanded

def build_tree_filter(label: str, nodes: list[dict], key: str, checked: list[str] = [], expanded: list[str] = [], height = 200):
    if key not in ss:
        ss[key] = None
        st.rerun()
    
    # If 'all' is in checked, collect all values
    if 'all' in checked:
        checked = _collect_all_values(nodes)
        
    with st.container(border=True):
        st.write(label)
        with st.container(height=height):
            selected = tree_select(nodes, 'leaf', key=key, checked=checked, expanded=expanded)
    
    return selected

@st.cache_data(show_spinner=False)
def build_nested_dict(df, columns):
    """
    Build a nested dictionary from a DataFrame based on a list of column names.
    Each column becomes a level in the dictionary, and the last column's values are collected in a list.
    
    Parameters:
        df (pd.DataFrame): The input DataFrame.
        columns (list): List of column names to nest by, in order.
        
    Returns:
        dict: A nested dictionary.
    """
    
    def recursive_dict():
        return defaultdict(recursive_dict)

    nested = recursive_dict()

    for _, row in df.iterrows():
        d = nested
        for col in columns[:-2]:
            d = d[row[col]]
        # Handle second last as key, last as value in a list
        key = row[columns[-2]]
        value = row[columns[-1]]
        d.setdefault(key, set()).add(value)

    # Convert sets to lists
    def convert(d):
        if isinstance(d, defaultdict):
            return {k: convert(v) for k, v in d.items()}
        elif isinstance(d, set):
            return list(d)
        else:
            return d

    return convert(nested)

#@st.cache_data(show_spinner=False)
def _get_label_and_value(item, current_value_col, current_label_col, current_filters, df):
    """Helper function to get label and value for a node."""
    query_conditions = [f"{col}=='{val}'" for col, val in current_filters.items()]
    #label_row = df.query(" and ".join(query_conditions)) if query_conditions else df[df[current_value_col] == item]
    label_row = df[df[current_value_col] == item]
    label = label_row.iloc[0][current_label_col] if not label_row.empty else item

    if current_value_col in [FUND_TYPE, HK_CODE]:
        parent_keys = list(current_filters.keys())
        parent_values = list(current_filters.values())
        parent_name = parent_values[-1]
        
        if parent_keys[-1] == FUND_TYPE:
            parent_name = parent_values[-2]
        
        node_value = f"{current_value_col}:{parent_name}:{item}"
    else:
        node_value = f"{current_value_col}:{item}"

    return label, node_value

#@st.cache_data(show_spinner=False)
def create_tree_nodes(data, column_mapping, df, parent_filters=None, level=0):
    """
    Convert nested dictionary to tree select nodes structure with custom labels
    """
    nodes = []
    if parent_filters is None:
        parent_filters = {}

    if isinstance(data, dict):
        for key, value in data.items():
            current_value_col = column_mapping[level]['value']
            current_label_col = column_mapping[level]['label']

            current_filters = parent_filters.copy()
            current_filters[current_value_col] = key

            label, node_value = _get_label_and_value(key, current_value_col, current_label_col, current_filters, df)

            node = {"label": label, "value": node_value}
            children = create_tree_nodes(value, column_mapping, df, current_filters, level + 1)
            if children:
                node["children"] = children
            nodes.append(node)

    elif isinstance(data, list):
        current_value_col = column_mapping[level]['value']
        current_label_col = column_mapping[level]['label']

        for item in data:
            current_filters = parent_filters.copy()
            
            label, node_value = _get_label_and_value(item, current_value_col, current_label_col, current_filters, df)

            nodes.append({"label": label, "value": node_value})

    return nodes