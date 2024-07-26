import streamlit as st
from st_oauth import st_oauth

def home_page():
    st.write("# Welcome to Stilson Dashboard! 👋")
    st.write("For any bugs, please report them to Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')

# Open css file
st.markdown('<style>' + open('./styles/style.css').read() + '</style>', unsafe_allow_html=True)

pages = [st.Page(home_page, title="Home")]

nav = st.navigation(pages)
nav.run()

id = st_oauth('fwdoauth')

print(id)