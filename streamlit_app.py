import streamlit as st
from st_oauth import st_oauth
from tools import snowflake

st.set_page_config(layout="wide", page_title='Stilson Dashboard', page_icon='styles/fwd_ico.png')

# Open css file
st.markdown('<style>' + open('./styles/style.css').read() + '</style>', unsafe_allow_html=True)

if "pages" not in st.session_state:
    pages = st.session_state["pages"] = [st.Page("pages/callback.py", title="Callback")]
    nav = st.navigation(pages)
    nav.run()
else:
    pages = st.session_state["pages"]

if "fwdoauth" in st.secrets:
    hide_github_icon = """
    #GithubIcon {
        visibility: hidden;
    }
    """
    st.markdown(hide_github_icon, unsafe_allow_html=True)
    id = st_oauth('fwdoauth')

if ("ST_OAUTH" in st.session_state or "fwdoauth" not in st.secrets) and "callback_removed" not in st.session_state:
    pages = st.session_state["pages"] = [st.Page("pages/home.py", title="Home"), st.Page("pages/asset_allocation.py", title="Asset Allocation"), st.Page("pages/breakdown.py", title="Breakdown")]
    st.session_state["callback_removed"] = True
    st.rerun()

nav = st.navigation(pages)
nav.run()

if "conn" not in st.session_state:
    snowflake.connect_snowflake()