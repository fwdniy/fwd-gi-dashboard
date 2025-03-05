import streamlit as st
from utils.interface.menu import menu
from streamlit_js_eval import streamlit_js_eval
from streamlit import session_state as ss

streamlit_js_eval(js_expressions="window.innerWidth", key='SCR')

menu('streamlit_app.py')

st.write(f'# Stilson Dashboard')
st.write(f'## Welcome {ss["nickname"]}! 👋')
st.write(f'For any enhancements or bugs, please contact {st.secrets["admin"]["name"]} via Teams or email ({st.secrets["admin"]["email"]})')
st.write(f'Your permissions are set to {ss['permissions']}.')

with st.expander("Release Notes", True):
    st.write("2025/01/10")
    st.write("- Repos: initial version released")
    st.write("2025/01/07")
    st.write(" - Permissions: fixed issue with case sensitivity of user email and permissions")
    st.write("2025/01/02")
    st.write(" - Permissions: added user permissions to restrict access to certain pages")
    st.write("2024/12/21")
    st.write(" - Curves: added implied forward rates")
    st.write(" - Funnelweb Pivot Table: enhanced interface and added weighted average metrics")
    st.write("2024/12/20")
    st.write(" - Hong Kong - Asset Allocation: Changed WARF table to exclude repos and bond forwards")
