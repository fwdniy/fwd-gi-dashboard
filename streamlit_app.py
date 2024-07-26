import streamlit as st
from st_oauth import st_oauth

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')

# Open css file
st.markdown('<style>' + open('./styles/style.css').read() + '</style>', unsafe_allow_html=True)

pages = [st.Page("pages/callback.py", title="Callback"), st.Page("pages/home.py", title="Home"), st.Page("pages/asset_allocation.py", title="Asset Allocation")]

if st.secrets != {}:
    id = st_oauth('fwdoauth')

if 'ST_OAUTH' in st.session_state or st.secrets == {}:
    pages = st.session_state["pages"]

nav = st.navigation(pages)
nav.run()