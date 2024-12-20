from streamlit_tree_select import tree_select
import streamlit as st

def build_tree_selectors(title, data, key, checked, expanded, height = 200):
    with st.container(border=True):
        st.write(title)
        with st.container(height=height):
            tree_select(data, 'leaf', key=key, checked=checked, expanded=expanded)