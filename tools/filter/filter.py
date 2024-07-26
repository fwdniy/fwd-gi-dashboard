import streamlit as st
from tools.filter.filter_data import get_lbu_data

def build_lbu_filter():
    lbu_df = get_lbu_data()
    
    st.dataframe(lbu_df)