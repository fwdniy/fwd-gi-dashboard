import streamlit as st
from st_oauth import st_oauth

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')

def home_page():
    st.write("# Welcome to Stilson Dashboard! 👋")
    st.write("For any bugs, please report them to Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")
    st.write(id)

def home_page2():
    st.write("# Welcome to Stilson Dashboard 2! 👋")
    st.write("For any bugs, please report them to Nicolas Au-Yeung via Teams or email (nicolas.au.yeung@fwd.com)")
    st.write(id)

# Open css file
st.markdown('<style>' + open('./styles/style.css').read() + '</style>', unsafe_allow_html=True)

id = st_oauth('fwdoauth')

#pages = [st.Page(home_page, title="Home"), st.Page(home_page2, title="Home2")]

#nav = st.navigation(pages)
#nav.run()