import streamlit as st
from db.data.fx import get_fx_list

def build_fx_filter(key_suffix=''):
    key = 'selected_currency' + key_suffix
    
    fx = get_fx_list()
    
    selected_fx = st.selectbox('Currency', fx, key=key, index=fx.index('USD') if 'USD' in fx else 0)
    
    return selected_fx