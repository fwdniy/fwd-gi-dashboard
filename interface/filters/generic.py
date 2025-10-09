import streamlit as st
from streamlit import session_state as ss

def build_multi_select_filter(label: str, mappings: dict[str, str], key: str, default: str = None, disabled: bool = False, max_selections: int = 9999):
    selection = st.multiselect(label, mappings.keys(), key=key, default=default, disabled=disabled, max_selections=max_selections)
    selection_converted = ss[f'{key}_selected'] = [mappings[column] for column in selection]
    
    return selection, selection_converted