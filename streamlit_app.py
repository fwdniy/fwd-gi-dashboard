import streamlit as st
from utils.interface.menu import menu
from streamlit_js_eval import streamlit_js_eval

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')
streamlit_js_eval(js_expressions="window.innerWidth", key='SCR')

menu('Home')

st.write("# Welcome to the Stilson Dashboard! 👋")
st.write("For any enhancements or bugs, please contact Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")

with st.expander("Change Notes", True):
    st.write("2024/12/21")
    st.write(" - Curves: added implied forward rates")
    st.write(" - Funnelweb Pivot Table: enhanced interface and added weighted average metrics")
    st.write("2024/12/20")
    st.write(" - Hong Kong - Asset Allocation: Changed WARF table to exclude repos and bond forwards")