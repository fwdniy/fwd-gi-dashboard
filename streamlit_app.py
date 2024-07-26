import streamlit as st
from st_oauth import st_oauth

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')

def callback():
    st.switch_page("Home")

# Open css file
st.markdown('<style>' + open('./styles/style.css').read() + '</style>', unsafe_allow_html=True)

id = st_oauth('fwdoauth')

pages = [st.Page("pages/home.py", title="Home"), st.Page("pages/callback.py", title="Callback")]

nav = st.navigation(pages)
nav.run()