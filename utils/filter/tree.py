from streamlit_tree_select import tree_select
import streamlit as st
from streamlit import session_state as ss

def build_tree_selectors(title, data, key, checked, expanded, height = 200):
    if key not in ss:
        ss[key] = None
        st.rerun()
    
    with st.container(border=True):
        st.write(title)
        with st.container(height=height):
            selected = tree_select(data, 'leaf', key=key, checked=checked, expanded=expanded)
    
    return selected